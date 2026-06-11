"""Service seam: email versioning — two authors, supersede, approve/send gates."""

import pytest

from server.errors import Conflict
from server.services import emails as email_service, participations as participation_service
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


def test_sent_versions_are_never_superseded(session, participation):
    v1 = email_service.save_draft(session, participation["id"], "S", "B", author="agent")
    email_service.approve(session, v1["id"])
    email_service.mark_sent(session, v1["id"])
    v2 = email_service.save_draft(session, participation["id"], "Follow-up", "B2", author="agent")
    thread = participation_service.get_thread(session, participation["id"])
    by_version = {e["version"]: e["status"] for e in thread}
    assert by_version == {1: "sent", 2: "in_review"}
    assert v2["version"] == 2
