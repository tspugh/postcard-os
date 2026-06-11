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
    """Explicit, recorded state change. Phase 2a will additionally create a Gmail draft here
    (drafts-only OAuth scope) — the gate logic stays exactly this."""
    return email_service.approve(session, email_id)


@router.post("/{email_id}/mark-sent")
def mark_sent(email_id: uuid.UUID, session: Session = Depends(get_session)):
    return email_service.mark_sent(session, email_id)
