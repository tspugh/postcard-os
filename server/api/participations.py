import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.db import get_session
from server.services import participations as participation_service
from server.services.serialize import participation_to_dict

router = APIRouter(prefix="/participations", tags=["participations"])


@router.get("/{participation_id}")
def detail(participation_id: uuid.UUID, session: Session = Depends(get_session)):
    p = participation_service.get_participation(session, participation_id)
    return {
        **participation_to_dict(p),
        "thread": participation_service.get_thread(session, participation_id),
    }


@router.delete("/{participation_id}")
def detach(participation_id: uuid.UUID, session: Session = Depends(get_session)):
    return participation_service.remove_from_campaign(session, participation_id)


@router.post("/{participation_id}/status")
def set_status(participation_id: uuid.UUID, payload: dict, session: Session = Depends(get_session)):
    """Operator state corrections (logged). committed/waitlisted/paid have dedicated flows."""
    return participation_service.set_status(session, participation_id, payload.get("status"))


@router.post("/{participation_id}/commitment")
def record_commitment(participation_id: uuid.UUID, payload: dict, session: Session = Depends(get_session)):
    return participation_service.record_commitment(session, participation_id, payload.get("amount_cents"))


@router.post("/{participation_id}/waitlist")
def move_to_waitlist(participation_id: uuid.UUID, session: Session = Depends(get_session)):
    return participation_service.move_to_waitlist(session, participation_id)


@router.post("/{participation_id}/promote")
def promote(participation_id: uuid.UUID, payload: dict, session: Session = Depends(get_session)):
    """Operator-only: promotion re-runs the exclusivity check and requires the amount."""
    return participation_service.promote_from_waitlist(session, participation_id, payload.get("amount_cents"))


@router.patch("/{participation_id}/payment")
def payment(participation_id: uuid.UUID, payload: dict, session: Session = Depends(get_session)):
    return participation_service.record_payment(
        session,
        participation_id,
        payload.get("payment_status"),
        payload.get("payment_method"),
    )


@router.patch("/{participation_id}/fulfillment")
def fulfillment(participation_id: uuid.UUID, payload: dict, session: Session = Depends(get_session)):
    return participation_service.update_fulfillment(session, participation_id, payload)
