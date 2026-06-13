"""Service seam: email versioning — two authors, supersede, approve/send gates,
and the mail handoff (approved versions placed into the operator's mailbox as drafts)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from server.errors import Conflict, ValidationRejected
from server.models import Comment, Email, Interaction
from server.services import (
    comments as comment_service,
    emails as email_service,
    participations as participation_service,
    summary as summary_service,
)
from tests.conftest import make_researched


@pytest.fixture
def participation(session, campaign):
    b = make_researched(session)
    return participation_service.add_to_campaign(session, campaign["id"], b["id"])


def test_draft_save_versions_and_supersedes(session, participation):
    v1 = email_service.save_draft(session, participation["id"], "Subject A", "Body", author="agent")
    v2 = email_service.save_draft(session, participation["id"], "Subject B", "Body 2", author="agent")
    assert (v1["version"], v2["version"]) == (1, 2)
    thread = participation_service.get_thread(session, participation["id"])
    assert thread[0]["status"] == "in_review" and thread[0]["version"] == 2
    assert thread[1]["status"] == "superseded"


def test_operator_edit_creates_operator_attributed_version(session, participation):
    email_service.save_draft(session, participation["id"], "Agent draft", "Body", author="agent")
    edit = email_service.save_draft(session, participation["id"], "Tightened", "Better body", author="operator")
    assert edit["author"] == "operator"
    assert edit["version"] == 2


def test_approve_only_from_in_review(session, participation):
    v1 = email_service.save_draft(session, participation["id"], "S", "B", author="agent")
    email_service.save_draft(session, participation["id"], "S2", "B2", author="agent")
    with pytest.raises(Conflict, match="superseded"):
        email_service.approve(session, v1["id"])


def test_mark_sent_only_from_approved_and_advances_participation(session, participation):
    v1 = email_service.save_draft(session, participation["id"], "S", "B", author="agent")
    with pytest.raises(Conflict, match="Approve it first"):
        email_service.mark_sent(session, v1["id"])
    email_service.approve(session, v1["id"])
    sent = email_service.mark_sent(session, v1["id"])
    assert sent["status"] == "sent" and sent["sent_at"] is not None
    p = participation_service.get_participation(session, participation["id"])
    assert p.status == "contacted"


def test_handoff_only_for_approved_versions(session, participation):
    v1 = email_service.save_draft(session, participation["id"], "S", "B", author="agent")
    with pytest.raises(Conflict, match="still in review"):
        email_service.link_provider_draft(session, v1["id"], "gmail", "r-123")
    email_service.approve(session, v1["id"])
    linked = email_service.link_provider_draft(session, v1["id"], "gmail", "r-123")
    assert linked["delivery_provider"] == "gmail"
    assert linked["provider_draft_id"] == "r-123"
    assert linked["handed_off_at"] is not None
    assert linked["status"] == "approved"  # handoff is not a state change


def test_handoff_is_idempotent_but_rejects_a_second_draft(session, participation):
    v1 = email_service.save_draft(session, participation["id"], "S", "B", author="agent")
    email_service.approve(session, v1["id"])
    email_service.link_provider_draft(session, v1["id"], "gmail", "r-123")
    again = email_service.link_provider_draft(session, v1["id"], "gmail", "r-123")
    assert again["provider_draft_id"] == "r-123"
    with pytest.raises(Conflict, match="already linked"):
        email_service.link_provider_draft(session, v1["id"], "gmail", "r-456")


def test_handoff_rejects_unknown_provider_and_sent_versions(session, participation):
    v1 = email_service.save_draft(session, participation["id"], "S", "B", author="agent")
    email_service.approve(session, v1["id"])
    with pytest.raises(ValidationRejected, match="provider must be one of"):
        email_service.link_provider_draft(session, v1["id"], "outlook", "r-1")
    email_service.mark_sent(session, v1["id"])
    with pytest.raises(Conflict, match="'sent'"):
        email_service.link_provider_draft(session, v1["id"], "gmail", "r-1")


def test_campaign_board_lists_approved_awaiting_handoff(session, campaign, participation):
    v1 = email_service.save_draft(session, participation["id"], "The roofer spot", "Body", author="agent")
    board = summary_service.campaign_board(session, campaign["id"])
    assert board["approved_awaiting_handoff"] == []  # in_review is not handoff work
    email_service.approve(session, v1["id"])
    board = summary_service.campaign_board(session, campaign["id"])
    [item] = board["approved_awaiting_handoff"]
    assert item["email_id"] == v1["id"]
    assert item["to"] == "dana@summitroofing.example.com"
    assert item["subject"] == "The roofer spot" and item["body"] == "Body"
    email_service.link_provider_draft(session, v1["id"], "gmail", "r-123")
    board = summary_service.campaign_board(session, campaign["id"])
    assert board["approved_awaiting_handoff"] == []


def test_email_state_is_derived_for_display(session, campaign, participation):
    def state():
        [p] = summary_service.campaign_board(session, campaign["id"])["participations"]
        return p["email_state"]

    assert state() is None  # researched + attached, no draft yet
    v1 = email_service.save_draft(session, participation["id"], "S", "B", author="agent")
    assert state() == "draft_in_review"
    email_service.approve(session, v1["id"])
    assert state() == "approved"
    email_service.link_provider_draft(session, v1["id"], "gmail", "r-123")
    assert state() == "in_mailbox"
    email_service.mark_sent(session, v1["id"])
    assert state() == "sent"


def test_revision_feedback_flips_email_state(session, campaign, participation):
    """Operator comment newer than the draft → revisions_requested (on the agent's
    worklist); agent's next version → revised; operator resolve → back to plain review.
    Timestamps are set explicitly because now() is frozen within one test transaction."""
    t0 = datetime.now(timezone.utc) - timedelta(minutes=10)

    def state():
        [p] = summary_service.campaign_board(session, campaign["id"])["participations"]
        return p["email_state"]

    def backdate(model, row_id, ts):
        session.get(model, row_id).created_at = ts
        session.flush()

    v1 = email_service.save_draft(session, participation["id"], "S", "B", author="agent")
    backdate(Email, v1["id"], t0)
    assert state() == "draft_in_review"

    c = comment_service.add_comment(session, "email", v1["id"], "grant", "Too long — tighten it.")
    backdate(Comment, c["id"], t0 + timedelta(minutes=1))
    assert state() == "revisions_requested"
    board = summary_service.campaign_board(session, campaign["id"])
    [req] = board["revision_requests"]
    assert req["email_id"] == v1["id"] and req["unresolved_comments"] == 1
    assert req["subject"] == "S" and req["body"] == "B"  # agent revises against the actual draft

    v2 = email_service.save_draft(session, participation["id"], "S", "Tighter", author="agent")
    backdate(Email, v2["id"], t0 + timedelta(minutes=2))
    assert state() == "revised"
    assert summary_service.campaign_board(session, campaign["id"])["revision_requests"] == []

    comment_service.resolve_comment(session, c["id"])
    assert state() == "draft_in_review"


def test_list_emails_filters_by_status_and_feedback(session, campaign, participation):
    v1 = email_service.save_draft(session, participation["id"], "First", "Body", author="agent")
    email_service.approve(session, v1["id"])
    v2 = email_service.save_draft(session, participation["id"], "Second", "Body 2", author="agent")

    approved = email_service.list_emails(session, status="approved")
    assert [e["id"] for e in approved] == [v1["id"]]
    assert approved[0]["business_name"] == "Summit Roofing"
    assert approved[0]["participation_status"] == "prospecting"

    comment_service.add_comment(session, "email", uuid.UUID(v2["id"]), "grant", "Shorter.")
    flagged = email_service.list_emails(session, has_unresolved_comments=True)
    assert [e["id"] for e in flagged] == [v2["id"]]
    assert flagged[0]["unresolved_comments"] == 1
    assert email_service.list_emails(session, status="in_review", has_unresolved_comments=False) == []

    with pytest.raises(ValidationRejected, match="status must be one of"):
        email_service.list_emails(session, status="bogus")


def test_open_feedback_surfaces_unresolved_comments_with_context(session, campaign, participation):
    v1 = email_service.save_draft(session, participation["id"], "S", "B", author="agent")
    business_id = uuid.UUID(participation["business_id"])
    c_biz = comment_service.add_comment(session, "business", business_id, "grant", "Check the phone number")
    comment_service.add_comment(session, "email", uuid.UUID(v1["id"]), "grant", "Tighten the hook")

    fb = summary_service.open_feedback(session)
    assert {f["entity_type"] for f in fb} == {"business", "email"}
    email_item = next(f for f in fb if f["entity_type"] == "email")
    assert email_item["email_version"] == 1
    assert email_item["business_name"] == "Summit Roofing"
    assert email_item["participation_id"] == participation["id"]

    comment_service.resolve_comment(session, uuid.UUID(c_biz["id"]))
    assert {f["entity_type"] for f in summary_service.open_feedback(session)} == {"email"}

    # Both comments also landed on the card's timeline.
    types = list(session.scalars(select(Interaction.type).where(Interaction.business_id == business_id)))
    assert types.count("comment_added") == 2


def test_sent_versions_are_never_superseded(session, participation):
    v1 = email_service.save_draft(session, participation["id"], "S", "B", author="agent")
    email_service.approve(session, v1["id"])
    email_service.mark_sent(session, v1["id"])
    v2 = email_service.save_draft(session, participation["id"], "Follow-up", "B2", author="agent")
    thread = participation_service.get_thread(session, participation["id"])
    by_version = {e["version"]: e["status"] for e in thread}
    assert by_version == {1: "sent", 2: "in_review"}
    assert v2["version"] == 2
