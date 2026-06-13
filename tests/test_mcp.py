"""MCP contract seam via FastMCP's in-process client (TRD §6)."""

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from sqlalchemy import select

from server.db import SessionLocal
from server.mcp import build_mcp
from server.models import AgentActivity, Business
from tests.conftest import make_campaign, make_researched

EXPECTED_TOOLS = {
    "postcard_get_campaign_status",
    "postcard_create_campaign",
    "postcard_list_staged_leads",
    "postcard_stage_leads",
    "postcard_claim_lead",
    "postcard_submit_research",
    "postcard_update_business",
    "postcard_save_contact",
    "postcard_delete_contact",
    "postcard_disqualify_lead",
    "postcard_add_to_campaign",
    "postcard_remove_from_campaign",
    "postcard_save_email_draft",
    "postcard_get_comments",
    "postcard_record_commitment",
    "postcard_move_to_waitlist",
    "postcard_save_postcard_draft",
}


@pytest.fixture(scope="module")
def mcp():
    return build_mcp()


async def test_tool_list_matches_spec(mcp):
    async with Client(mcp) as client:
        tools = {t.name for t in await client.list_tools()}
    assert tools == EXPECTED_TOOLS


async def test_orientation_includes_settings_waitlists_and_pipeline(mcp, session):
    campaign = make_campaign(session)
    from server.services import participations as participation_service

    b = make_researched(session)
    p = participation_service.add_to_campaign(session, campaign["id"], b["id"])
    participation_service.move_to_waitlist(session, p["id"])
    session.commit()

    async with Client(mcp) as client:
        result = await client.call_tool("postcard_get_campaign_status", {})
    doc = result.data
    assert doc["settings"]["default_slot_price_cents"] == 29900
    assert "roofer" in doc["settings"]["categories"]
    assert doc["settings"]["seed_market"] == "Lafayette, IN"
    assert doc["pipeline_counts"]["researched"] == 1
    roofer = next(s for s in doc["campaign_board"]["slots"] if s["category"] == "roofer")
    assert [w["waitlist_order"] for w in roofer["waitlist"]] == [1]


async def test_validation_errors_are_actionable(mcp):
    async with Client(mcp) as client:
        result = await client.call_tool(
            "postcard_stage_leads", {"leads": [{"name": "No Website Inc", "category": "plumber"}]}
        )
        assert "Staging bar" in result.data["rejected"][0]["reason"]
        with pytest.raises(ToolError, match="not a valid business id"):
            await client.call_tool("postcard_claim_lead", {"business_id": "not-a-uuid"})


async def test_create_campaign_accepts_month_and_defaults_from_settings(mcp):
    async with Client(mcp) as client:
        result = await client.call_tool(
            "postcard_create_campaign", {"month": "2026-07", "deadline": "2026-06-25"}
        )
        doc = result.data
        assert doc["month"] == "2026-07-01"
        assert doc["name"] == "Lafayette, IN July 2026"
        assert doc["slot_price_cents"] == 29900
        with pytest.raises(ToolError, match="not a valid month"):
            await client.call_tool(
                "postcard_create_campaign", {"month": "July", "deadline": "2026-06-25"}
            )


async def test_no_campaign_errors_point_to_operator(mcp):
    """With no campaign in the system, campaign-dependent tools must say how to proceed:
    ask the operator (dashboard), or postcard_create_campaign on explicit instruction only."""
    import uuid as uuid_mod

    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="no active campaign"):
            await client.call_tool(
                "postcard_save_email_draft",
                {"participation_id": str(uuid_mod.uuid4()), "subject": "s", "body": "b"},
            )
        with pytest.raises(ToolError, match="postcard_create_campaign"):
            await client.call_tool(
                "postcard_add_to_campaign",
                {"campaign_id": str(uuid_mod.uuid4()), "business_id": str(uuid_mod.uuid4())},
            )


async def test_exclusivity_rejection_recommends_waitlist(mcp, session):
    campaign = make_campaign(session)
    from server.services import participations as participation_service

    b1 = make_researched(session, name="Summit Roofing")
    b2 = make_researched(session, name="Apex Roofing")
    p1 = participation_service.add_to_campaign(session, campaign["id"], b1["id"])
    p2 = participation_service.add_to_campaign(session, campaign["id"], b2["id"])
    participation_service.record_commitment(session, p1["id"], 29900)
    session.commit()

    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="postcard_move_to_waitlist"):
            await client.call_tool(
                "postcard_record_commitment", {"participation_id": p2["id"], "amount_cents": 25000}
            )
        moved = await client.call_tool("postcard_move_to_waitlist", {"participation_id": p2["id"]})
        assert moved.data["status"] == "waitlisted"


async def test_read_only_tools_mutate_nothing(mcp, session):
    make_researched(session)
    session.commit()
    with SessionLocal() as s:
        before = [(b.name, b.status, b.operator_viewed_at) for b in s.scalars(select(Business))]
    async with Client(mcp) as client:
        await client.call_tool("postcard_list_staged_leads", {})
        await client.call_tool("postcard_get_campaign_status", {})
    with SessionLocal() as s:
        after = [(b.name, b.status, b.operator_viewed_at) for b in s.scalars(select(Business))]
    assert before == after


async def test_every_call_logged_to_agent_activity(mcp):
    async with Client(mcp) as client:
        await client.call_tool("postcard_list_staged_leads", {})
        with pytest.raises(ToolError):
            await client.call_tool("postcard_claim_lead", {"business_id": "not-a-uuid"})
    with SessionLocal() as s:
        rows = list(s.scalars(select(AgentActivity).order_by(AgentActivity.created_at)))
    by_tool = {(r.tool_name, r.outcome) for r in rows}
    assert ("postcard_list_staged_leads", "ok") in by_tool
    assert ("postcard_claim_lead", "rejected") in by_tool


async def test_full_agent_flow_stage_research_draft(mcp, session):
    campaign = make_campaign(session)
    session.commit()
    async with Client(mcp) as client:
        staged = await client.call_tool(
            "postcard_stage_leads",
            {"leads": [{"name": "Wabash HVAC", "category": "hvac", "website": "wabashhvac.example.com"}]},
        )
        business_id = staged.data["staged"][0]["id"]
        await client.call_tool("postcard_claim_lead", {"business_id": business_id})
        researched = await client.call_tool(
            "postcard_submit_research",
            {
                "business_id": business_id,
                "research": {
                    "premise": "HVAC installer serving greater Lafayette; residential furnace and AC replacement.",
                    "hooks": ["24/7 emergency service since 1998"],
                    "evidence_urls": ["https://wabashhvac.example.com/about"],
                    "contacts": [
                        {
                            "email": "office@wabashhvac.example.com",
                            "email_source": "https://wabashhvac.example.com/contact",
                            "email_confidence": "listed",
                        }
                    ],
                },
            },
        )
        assert researched.data["status"] == "researched"
        attached = await client.call_tool(
            "postcard_add_to_campaign", {"campaign_id": campaign["id"], "business_id": business_id}
        )
        assert attached.data["asking_price_cents"] == 29900
        draft = await client.call_tool(
            "postcard_save_email_draft",
            {
                "participation_id": attached.data["id"],
                "subject": "The HVAC spot on July's Lafayette postcard",
                "body": "Hi — saw you've run 24/7 emergency service since 1998...",
            },
        )
        assert draft.data["status"] == "in_review"
        assert draft.data["author"] == "agent"


async def test_resources_present_and_single_sourced(mcp):
    async with Client(mcp) as client:
        uris = {str(r.uri) for r in await client.list_resources()}
        assert {
            "postcard://reference/workflow",
            "postcard://reference/quality-bars",
            "postcard://reference/email-expectations",
            "postcard://reference/sender",
            "postcard://reference/slot-spec",
            "postcard://reference/template",
            "postcard://reference/pricing",
        } <= uris
        workflow = await client.read_resource("postcard://reference/workflow")
        assert "postcard_get_campaign_status" in workflow[0].text
        pricing = await client.read_resource("postcard://reference/pricing")
        assert "$299.00" in pricing[0].text
