import uuid
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.db import get_session
from server.services import campaigns as campaign_service, participations as participation_service
from server.services.summary import campaign_board

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    month: date
    deadline: date
    name: str | None = None
    market: str | None = None


@router.get("")
def list_campaigns(session: Session = Depends(get_session)):
    return campaign_service.list_campaigns(session)


@router.post("")
def create_campaign(payload: CampaignCreate, session: Session = Depends(get_session)):
    return campaign_service.create_campaign(
        session, month=payload.month, deadline=payload.deadline, name=payload.name, market=payload.market
    )


@router.get("/{campaign_id}/board")
def board(campaign_id: uuid.UUID, session: Session = Depends(get_session)):
    """The Campaign screen in one document: slots + waitlists + roll-ups."""
    return campaign_board(session, campaign_id)


@router.post("/{campaign_id}/status")
def set_status(campaign_id: uuid.UUID, payload: dict, session: Session = Depends(get_session)):
    return campaign_service.set_campaign_status(session, campaign_id, payload.get("status"))


@router.get("/{campaign_id}/priority-prospects")
def priority_prospects(campaign_id: uuid.UUID, session: Session = Depends(get_session)):
    """Waitlisted/participated businesses from prior campaigns — one-click re-attach."""
    return campaign_service.priority_prospects(session, campaign_id)


@router.post("/{campaign_id}/participations")
def attach(campaign_id: uuid.UUID, payload: dict, session: Session = Depends(get_session)):
    return participation_service.add_to_campaign(
        session, campaign_id, uuid.UUID(payload["business_id"]), payload.get("category")
    )


@router.post("/{campaign_id}/waitlist-order")
def waitlist_order(campaign_id: uuid.UUID, payload: dict, session: Session = Depends(get_session)):
    """Manual reorder: {category, participation_ids: [...]} listing the full waitlist."""
    return participation_service.reorder_waitlist(
        session, campaign_id, payload.get("category"), payload.get("participation_ids") or []
    )
