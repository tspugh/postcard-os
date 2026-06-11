import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.db import get_session
from server.services import businesses as business_service, contacts as contact_service
from server.services.documents import business_detail_document, list_business_documents
from server.services.summary import summary_strip

router = APIRouter(tags=["businesses"])


@router.get("/summary")
def dashboard_summary(session: Session = Depends(get_session)):
    """Summary strip: spots filled/remaining, revenue committed vs collected, drafts
    awaiting review, waitlist count, deadline countdown, unviewed counts."""
    return summary_strip(session)


@router.get("/businesses")
def list_businesses(session: Session = Depends(get_session)):
    """Leads view document: businesses with their most relevant participation inline."""
    return list_business_documents(session)


@router.post("/businesses/stage")
def stage_leads(payload: dict, session: Session = Depends(get_session)):
    """Manual staging from the dashboard — same bar as the agent tool."""
    return business_service.stage_leads(session, payload.get("leads") or [], source="operator")


@router.get("/businesses/{business_id}")
def business_detail(business_id: uuid.UUID, session: Session = Depends(get_session)):
    """Drawer document: research, contacts, comments, participations with email threads
    and state changes. Fetching marks the record viewed (clears the 'unviewed' badge)."""
    return business_detail_document(session, business_id)


@router.patch("/businesses/{business_id}")
def update_business(business_id: uuid.UUID, fields: dict, session: Session = Depends(get_session)):
    return business_service.update_business(session, business_id, fields)


@router.post("/businesses/{business_id}/disqualify")
def disqualify(business_id: uuid.UUID, payload: dict, session: Session = Depends(get_session)):
    return business_service.disqualify(session, business_id, payload.get("dq_code"), payload.get("reason"))


@router.post("/businesses/{business_id}/contacts")
def save_contact(business_id: uuid.UUID, payload: dict, session: Session = Depends(get_session)):
    contact_id = payload.pop("contact_id", None)
    return contact_service.save_contact(
        session, business_id, payload, contact_id=uuid.UUID(contact_id) if contact_id else None
    )


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: uuid.UUID, session: Session = Depends(get_session)):
    return contact_service.delete_contact(session, contact_id)
