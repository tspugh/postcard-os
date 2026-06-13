import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.db import get_session
from server.services import emails as email_service

router = APIRouter(prefix="/emails", tags=["emails"])


@router.post("")
def operator_draft(payload: dict, session: Session = Depends(get_session)):
    """Operator edit: saves the next version, attributed to the operator."""
    return email_service.save_draft(
        session,
        uuid.UUID(payload["participation_id"]),
        payload.get("subject"),
        payload.get("body"),
        author="operator",
    )


@router.post("/{email_id}/approve")
def approve(email_id: uuid.UUID, session: Session = Depends(get_session)):
    """Explicit, recorded state change. Approval also puts the version on the agent's
    mail-handoff worklist (approved_awaiting_handoff): the agent places it into the
    operator's mailbox as a draft via their mail connector and links it back with
    postcard_link_mail_draft. The server never talks to Gmail and never sends."""
    return email_service.approve(session, email_id)


@router.post("/{email_id}/mark-sent")
def mark_sent(email_id: uuid.UUID, session: Session = Depends(get_session)):
    return email_service.mark_sent(session, email_id)
