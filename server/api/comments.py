import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.db import get_session
from server.services import comments as comment_service

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("")
def list_comments(
    entity_type: str,
    entity_id: uuid.UUID,
    unresolved_only: bool = False,
    session: Session = Depends(get_session),
):
    return comment_service.list_comments(session, entity_type, entity_id, unresolved_only=unresolved_only)


@router.post("")
def add_comment(payload: dict, session: Session = Depends(get_session)):
    return comment_service.add_comment(
        session,
        payload.get("entity_type"),
        uuid.UUID(payload["entity_id"]),
        payload.get("author", "grant"),
        payload.get("body"),
        slot_number=payload.get("slot_number"),
    )


@router.post("/{comment_id}/resolve")
def resolve(comment_id: uuid.UUID, payload: dict | None = None, session: Session = Depends(get_session)):
    resolved = True if payload is None else bool(payload.get("resolved", True))
    return comment_service.resolve_comment(session, comment_id, resolved)
