"""Service seam: participations — exclusivity, waitlist, promotion, payments, snapshots."""

import pytest

from server.errors import Conflict, ValidationRejected
from server.services import campaigns as campaign_service, participations as participation_service
from server.services.settings import update_settings
from server.services.summary import campaign_board
from tests.conftest import make_campaign, make_researched


def attach(session, campaign, name="Summit Roofing", category="roofer"):
    b = make_researched(session, name=name, category=category)
    return participation_service.add_to_campaign(session, campaign["id"], b["id"])


def test_attach_requires_researched(session, campaign):
    from server.services import businesses as business_service
    from tests.conftest import make_lead

    lead = make_lead(session)
    with pytest.raises(Conflict, match="not 'researched'"):
        participation_service.add_to_campaign(session, campaign["id"], lead["id"])


def test_asking_price_snapshot_survives_settings_change(session, campaign):
    p = attach(session, campaign)
    assert p["asking_price_cents"] == 29900
    update_settings(session, {"default_slot_price_cents": 39900})
    refetched = participation_service.get_participation(session, p["id"])
    assert refetched.asking_price_cents == 29900
    later = make_campaign(session, name="Next Run")
    assert later["slot_price_cents"] == 39900


def test_detach_blocked_past_contacted(session, campaign):
    p = attach(session, campaign)
    participation_service.set_status(session, p["id"], "interested")
    with pytest.raises(Conflict, match="prospecting or contacted"):
        participation_service.remove_from_campaign(session, p["id"])


def test_second_commitment_in_category_rejected_with_waitlist_recommendation(session, campaign):
    p1 = attach(session, campaign, name="Summit Roofing")
    p2 = attach(session, campaign, name="Apex Roofing")
    participation_service.record_commitment(session, p1["id"], 29900)
    with pytest.raises(Conflict) as e:
        participation_service.record_commitment(session, p2["id"], 25000)
    assert "already won by 'Summit Roofing'" in str(e.value)
    assert "postcard_move_to_waitlist" in str(e.value)


def test_commitment_assigns_slot_and_fills_campaign(session, campaign):
    p = attach(session, campaign)
    out = participation_service.record_commitment(session, p["id"], 32000)
    assert out["status"] == "committed"
    assert out["slot_number"] == 1
    assert out["committed_amount_cents"] == 32000
    board = campaign_board(session, campaign["id"])
    assert board["slots_filled"] == 1
    assert board["committed_cents"] == 32000
    assert board["campaign"]["status"] == "filling"


def test_waitlist_append_keeps_dense_order_and_reorder_persists(session, campaign):
    winner = attach(session, campaign, name="Summit Roofing")
    participation_service.record_commitment(session, winner["id"], 29900)
    others = [attach(session, campaign, name=f"Roofer {i}") for i in range(3)]
    waitlisted = [participation_service.move_to_waitlist(session, p["id"]) for p in others]
    assert [w["waitlist_order"] for w in waitlisted] == [1, 2, 3]
    ids = [w["id"] for w in waitlisted]
    reordered = participation_service.reorder_waitlist(session, campaign["id"], "roofer", [ids[2], ids[0], ids[1]])
    assert [r["id"] for r in reordered] == [ids[2], ids[0], ids[1]]
    assert [r["waitlist_order"] for r in reordered] == [1, 2, 3]


def test_promotion_blocked_while_slot_occupied_succeeds_after_decline(session, campaign):
    winner = attach(session, campaign, name="Summit Roofing")
    participation_service.record_commitment(session, winner["id"], 29900)
    runner_up = attach(session, campaign, name="Apex Roofing")
    runner_up = participation_service.move_to_waitlist(session, runner_up["id"])
    with pytest.raises(Conflict, match="still occupied"):
        participation_service.promote_from_waitlist(session, runner_up["id"], 29900)
    participation_service.set_status(session, winner["id"], "declined")
    with pytest.raises(ValidationRejected, match="requires the committed amount"):
        participation_service.promote_from_waitlist(session, runner_up["id"], None)
    promoted = participation_service.promote_from_waitlist(session, runner_up["id"], 27500)
    assert promoted["status"] == "committed"
    assert promoted["waitlist_order"] is None
    assert promoted["slot_number"] is not None


def test_promotion_renumbers_remaining_waitlist(session, campaign):
    others = [attach(session, campaign, name=f"Roofer {i}") for i in range(3)]
    w = [participation_service.move_to_waitlist(session, p["id"]) for p in others]
    participation_service.promote_from_waitlist(session, w[0]["id"], 29900)
    board = campaign_board(session, campaign["id"])
    roofer_slot = next(s for s in board["slots"] if s["category"] == "roofer")
    assert [x["waitlist_order"] for x in roofer_slot["waitlist"]] == [1, 2]


def test_payment_recordable_only_at_committed(session, campaign):
    p = attach(session, campaign)
    with pytest.raises(Conflict, match="recordable only on committed"):
        participation_service.record_payment(session, p["id"], "paid", "cash")
    participation_service.record_commitment(session, p["id"], 29900)
    paid = participation_service.record_payment(session, p["id"], "paid", "paypal")
    assert paid["status"] == "paid"
    assert paid["paid_at"] is not None
    board = campaign_board(session, campaign["id"])
    assert board["collected_cents"] == 29900


def test_fulfillment_editable_only_at_committed_and_validates_keys(session, campaign):
    p = attach(session, campaign)
    with pytest.raises(Conflict, match="unlocks at 'committed'"):
        participation_service.update_fulfillment(session, p["id"], {"logo_received": True})
    participation_service.record_commitment(session, p["id"], 29900)
    with pytest.raises(ValidationRejected, match="Unknown fulfillment fields"):
        participation_service.update_fulfillment(session, p["id"], {"shipped": True})
    out = participation_service.update_fulfillment(
        session, p["id"], {"logo_received": True, "offer_confirmed": True, "artwork_approved": True}
    )
    assert out["fulfillment_progress"] == "3/3"


def test_campaign_archive_reversible_only_to_completed_never_deleted(session, campaign):
    campaign_service.set_campaign_status(session, campaign["id"], "archived")
    with pytest.raises(Conflict, match="unarchived back to 'completed'"):
        campaign_service.set_campaign_status(session, campaign["id"], "filling")
    out = campaign_service.set_campaign_status(session, campaign["id"], "completed")
    assert out["status"] == "completed"


def test_waitlisted_surface_as_priority_prospects_next_campaign(session, campaign):
    winner = attach(session, campaign, name="Summit Roofing")
    participation_service.record_commitment(session, winner["id"], 29900)
    runner_up = attach(session, campaign, name="Apex Roofing")
    participation_service.move_to_waitlist(session, runner_up["id"])
    campaign_service.set_campaign_status(session, campaign["id"], "completed")
    next_campaign = make_campaign(session, name="August Run")
    prospects = campaign_service.priority_prospects(session, next_campaign["id"])
    names = {p["business"]["name"]: p["reason"] for p in prospects}
    assert "Apex Roofing" in names and "waitlisted" in names["Apex Roofing"]
    assert "Summit Roofing" in names and "participated" in names["Summit Roofing"]
