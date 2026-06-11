"""HTTP seam: dashboard contracts — composite shapes, viewed-marking, operator actions."""

import pytest
from fastapi.testclient import TestClient

from server.services import emails as email_service, participations as participation_service
from tests.conftest import make_campaign, make_researched


@pytest.fixture(scope="module")
def client():
    from server.app import app

    with TestClient(app) as c:
        yield c


def test_settings_roundtrip(client):
    s = client.get("/api/settings").json()
    assert s["default_slot_price_cents"] == 29900
    assert len(s["categories"]) == 8
    patched = client.patch("/api/settings", json={"outreach_instructions": "Plain, neighborly, no hype."})
    assert patched.status_code == 200
    assert patched.json()["outreach_instructions"] == "Plain, neighborly, no hype."


def test_manual_staging_enforces_bar(client):
    r = client.post("/api/businesses/stage", json={"leads": [{"name": "X", "category": "plumber"}]})
    assert r.status_code == 200
    assert "Staging bar" in r.json()["rejected"][0]["reason"]


def test_business_detail_marks_viewed(client, session):
    b = make_researched(session)
    session.commit()
    assert b["operator_viewed_at"] is None
    detail = client.get(f"/api/businesses/{b['id']}").json()
    assert detail["operator_viewed_at"] is not None
    assert detail["contacts"][0]["email"] == "dana@summitroofing.example.com"


def test_summary_strip_rollups(client, session):
    campaign = make_campaign(session)
    b = make_researched(session)
    p = participation_service.add_to_campaign(session, campaign["id"], b["id"])
    participation_service.record_commitment(session, p["id"], 31000)
    email_service.save_draft(session, p["id"], "S", "B", author="agent")
    session.commit()
    strip = client.get("/api/summary").json()
    assert strip["drafts_awaiting_review"] == 1
    assert strip["campaign"]["slots_filled"] == 1
    assert strip["campaign"]["committed_cents"] == 31000
    assert strip["campaign"]["collected_cents"] == 0
    assert "scarcity" in strip["campaign"]


def test_domain_errors_map_to_http_statuses(client, session):
    campaign = make_campaign(session)
    b = make_researched(session)
    p = participation_service.add_to_campaign(session, campaign["id"], b["id"])
    session.commit()
    r = client.post(f"/api/participations/{p['id']}/promote", json={"amount_cents": 29900})
    assert r.status_code == 409
    assert "waitlisted" in r.json()["detail"]
    r404 = client.get("/api/participations/00000000-0000-0000-0000-000000000000")
    assert r404.status_code == 404


def test_approve_copy_marksent_flow(client, session):
    campaign = make_campaign(session)
    b = make_researched(session)
    p = participation_service.add_to_campaign(session, campaign["id"], b["id"])
    draft = email_service.save_draft(session, p["id"], "S", "B", author="agent")
    session.commit()
    premature = client.post(f"/api/emails/{draft['id']}/mark-sent")
    assert premature.status_code == 409
    approved = client.post(f"/api/emails/{draft['id']}/approve")
    assert approved.json()["status"] == "approved"
    sent = client.post(f"/api/emails/{draft['id']}/mark-sent")
    assert sent.json()["status"] == "sent"
    detail = client.get(f"/api/participations/{p['id']}").json()
    assert detail["status"] == "contacted"
    assert detail["thread"][0]["status"] == "sent"


def test_operator_edit_via_rest_is_next_version(client, session):
    campaign = make_campaign(session)
    b = make_researched(session)
    p = participation_service.add_to_campaign(session, campaign["id"], b["id"])
    email_service.save_draft(session, p["id"], "Agent subject", "B", author="agent")
    session.commit()
    edit = client.post(
        "/api/emails", json={"participation_id": p["id"], "subject": "Fixed subject", "body": "B2"}
    ).json()
    assert edit["author"] == "operator"
    assert edit["version"] == 2


def test_campaign_board_and_waitlist_reorder_endpoint(client, session):
    campaign = make_campaign(session)
    ids = []
    for i in range(2):
        b = make_researched(session, name=f"Roofer {i}")
        p = participation_service.add_to_campaign(session, campaign["id"], b["id"])
        ids.append(participation_service.move_to_waitlist(session, p["id"])["id"])
    session.commit()
    board = client.get(f"/api/campaigns/{campaign['id']}/board").json()
    roofer = next(s for s in board["slots"] if s["category"] == "roofer")
    assert len(roofer["waitlist"]) == 2
    r = client.post(
        f"/api/campaigns/{campaign['id']}/waitlist-order",
        json={"category": "roofer", "participation_ids": [ids[1], ids[0]]},
    )
    assert [x["id"] for x in r.json()] == [ids[1], ids[0]]


def test_activity_feed_endpoint(client):
    r = client.get("/api/activity")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
