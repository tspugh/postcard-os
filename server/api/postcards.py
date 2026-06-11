import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.db import get_session
from server.services import postcards as postcard_service

router = APIRouter(prefix="/postcards", tags=["postcards"])


@router.get("/{campaign_id}")
def list_drafts(campaign_id: uuid.UUID, session: Session = Depends(get_session)):
    return postcard_service.list_drafts(session, campaign_id)


@router.get("/{campaign_id}/render")
def render(campaign_id: uuid.UUID, version: int | None = None, session: Session = Depends(get_session)):
    """Sanitized HTML for the dashboard's sandboxed iframe (scripts disabled)."""
    return postcard_service.render(session, campaign_id, version=version)
