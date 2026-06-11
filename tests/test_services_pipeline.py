"""Service seam: enrichment state machine, staging/research bars, DQ guards, contact CRUD."""

from datetime import datetime, timedelta, timezone

import pytest

from server.errors import Conflict, ValidationRejected
from server.models import Business
from server.services import businesses as business_service, contacts as contact_service
from server.services import participations as participation_service
from tests.conftest import RESEARCH, make_campaign, make_lead, make_researched


def test_staging_without_website_rejected_with_bar_restated(session):
    result = business_service.stage_leads(session, [{"name": "No Web LLC", "category": "plumber"}])
    assert result["staged"] == []
    assert "website" in result["rejected"][0]["reason"]
    assert "Staging bar" in result["rejected"][0]["reason"]


def test_duplicate_staging_names_existing_record(session):
    make_lead(session, name="Summit Roofing")
    result = business_service.stage_leads(
        session, [{"name": "summit  roofing!", "category": "roofer", "website": "https://other.example.com"}]
    )
    assert result["staged"] == []
    assert "Summit Roofing" in result["rejected"][0]["reason"]
    assert "never merged" in result["rejected"][0]["reason"]


def test_disqualified_lead_never_restaged(session):
    lead = make_lead(session)
    business_service.disqualify(session, lead["id"], "defunct")
    result = business_service.stage_leads(
        session, [{"name": "Summit Roofing", "category": "roofer", "website": "https://x.example.com"}]
    )
    assert result["staged"] == []
    assert "disqualified" in result["rejected"][0]["reason"]


def test_double_claim_fails(session):
    lead = make_lead(session)
    business_service.claim_lead(session, lead["id"])
    with pytest.raises(Conflict, match="already claimed"):
        business_service.claim_lead(session, lead["id"])


def test_stale_claim_reclaimable(session):
    lead = make_lead(session)
    business_service.claim_lead(session, lead["id"])
    b = session.get(Business, lead["id"])
    b.claimed_at = datetime.now(timezone.utc) - timedelta(hours=2)
    session.flush()
    reclaimed = business_service.claim_lead(session, lead["id"])
    assert reclaimed["status"] == "researching"


def test_research_bar_rejected_listing_missing_pieces(session):
    lead = make_lead(session)
    business_service.claim_lead(session, lead["id"])
    with pytest.raises(ValidationRejected) as e:
        business_service.submit_research(session, lead["id"], {"premise": "", "hooks": [], "evidence_urls": [], "contacts": []})
    msg = str(e.value)
    for piece in ("premise", "hook", "evidence", "contact"):
        assert piece in msg
    assert "Research bar" in msg


def test_research_contact_without_reachability_rejected(session):
    lead = make_lead(session)
    business_service.claim_lead(session, lead["id"])
    bad = dict(RESEARCH, contacts=[{"name": "Ghost"}])
    with pytest.raises(ValidationRejected, match="email or a phone"):
        business_service.submit_research(session, lead["id"], bad)


def test_research_unclaimed_rejected(session):
    lead = make_lead(session)
    with pytest.raises(Conflict, match="Claim it first"):
        business_service.submit_research(session, lead["id"], dict(RESEARCH))


def test_submit_research_creates_contact_rows_and_clears_claim(session):
    b = make_researched(session)
    assert b["status"] == "researched"
    assert b["claimed_at"] is None
    assert len(b["contacts"]) == 1
    assert b["contacts"][0]["is_primary"] is True


def test_dq_requires_valid_code_and_other_requires_note(session):
    lead = make_lead(session)
    with pytest.raises(ValidationRejected, match="not a disqualification code"):
        business_service.disqualify(session, lead["id"], "bored")
    with pytest.raises(ValidationRejected, match="requires a free-text reason"):
        business_service.disqualify(session, lead["id"], "other")
    out = business_service.disqualify(session, lead["id"], "other", "operator request")
    assert out["status"] == "disqualified"


def test_dq_blocked_on_active_participation(session):
    b = make_researched(session)
    campaign = make_campaign(session)
    participation_service.add_to_campaign(session, campaign["id"], b["id"])
    with pytest.raises(Conflict, match="active participation"):
        business_service.disqualify(session, b["id"], "bad_fit")


def test_disqualified_excluded_from_staged_list_and_unclaimable(session):
    lead = make_lead(session)
    business_service.disqualify(session, lead["id"], "defunct")
    assert business_service.list_staged(session) == []
    with pytest.raises(Conflict, match="never re-researched"):
        business_service.claim_lead(session, lead["id"])


def test_contact_upsert_corrects_and_one_primary_enforced(session):
    b = make_researched(session)
    second = contact_service.save_contact(
        session, b["id"], {"name": "Pat", "phone": "765-555-0100", "is_primary": True}
    )
    assert second["is_primary"] is True
    first = next(c for c in business_service.get_business(session, b["id"]).contacts if c.name == "Dana Summit")
    assert first.is_primary is False
    fixed = contact_service.save_contact(session, b["id"], {"phone": "765-555-0199"}, contact_id=second["id"])
    assert fixed["phone"] == "765-555-0199"


def test_last_contact_delete_blocked_on_active_advertiser(session):
    b = make_researched(session)
    campaign = make_campaign(session)
    participation_service.add_to_campaign(session, campaign["id"], b["id"])
    contact_id = b["contacts"][0]["id"]
    with pytest.raises(Conflict, match="last reachable contact"):
        contact_service.delete_contact(session, contact_id)
    # without an active participation the delete goes through
    b2 = make_researched(session, name="Rapids Plumbing", category="plumber")
    out = contact_service.delete_contact(session, b2["contacts"][0]["id"])
    assert out["deleted"]


def test_update_business_rejects_unknown_fields(session):
    b = make_researched(session)
    with pytest.raises(ValidationRejected, match="Updatable fields"):
        business_service.update_business(session, b["id"], {"website_rank": 3})
    out = business_service.update_business(session, b["id"], {"service_area": "Tippecanoe County"})
    assert out["service_area"] == "Tippecanoe County"
