"""JSON-ready dict serializers shared by REST and MCP."""

from server.models import (
    AgentActivity,
    Business,
    Campaign,
    Comment,
    Contact,
    Email,
    FULFILLMENT_CHECKLIST_KEYS,
    Participation,
    PostcardDraft,
)


def _iso(dt):
    return dt.isoformat() if dt is not None else None


def contact_to_dict(c: Contact) -> dict:
    return {
        "id": str(c.id),
        "business_id": str(c.business_id),
        "name": c.name,
        "title": c.title,
        "email": c.email,
        "email_source": c.email_source,
        "email_confidence": c.email_confidence,
        "phone": c.phone,
        "is_primary": c.is_primary,
    }


def business_to_dict(b: Business, include_contacts: bool = True) -> dict:
    out = {
        "id": str(b.id),
        "name": b.name,
        "category": b.category,
        "website": b.website,
        "address": b.address,
        "service_area": b.service_area,
        "premise": b.premise,
        "hooks": b.hooks or [],
        "evidence_urls": b.evidence_urls or [],
        "status": b.status,
        "dq_code": b.dq_code,
        "dq_reason": b.dq_reason,
        "source": b.source,
        "claimed_at": _iso(b.claimed_at),
        "operator_viewed_at": _iso(b.operator_viewed_at),
        "created_at": _iso(b.created_at),
    }
    if include_contacts:
        out["contacts"] = [contact_to_dict(c) for c in b.contacts]
    return out


def campaign_to_dict(c: Campaign) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "market": c.market,
        "month": c.month.isoformat(),
        "deadline": c.deadline.isoformat(),
        "slot_price_cents": c.slot_price_cents,
        "total_slots": c.total_slots,
        "status": c.status,
        "created_at": _iso(c.created_at),
    }


def fulfillment_progress(p: Participation) -> str:
    done = sum(1 for k in FULFILLMENT_CHECKLIST_KEYS if (p.fulfillment or {}).get(k) is True)
    return f"{done}/{len(FULFILLMENT_CHECKLIST_KEYS)}"


def participation_to_dict(p: Participation, business_name: str | None = None) -> dict:
    return {
        "id": str(p.id),
        "campaign_id": str(p.campaign_id),
        "business_id": str(p.business_id),
        "business_name": business_name if business_name is not None else (p.business.name if p.business else None),
        "category": p.category,
        "status": p.status,
        "asking_price_cents": p.asking_price_cents,
        "committed_amount_cents": p.committed_amount_cents,
        "payment_status": p.payment_status,
        "payment_method": p.payment_method,
        "paid_at": _iso(p.paid_at),
        "waitlist_order": p.waitlist_order,
        "fulfillment": p.fulfillment or {},
        "fulfillment_progress": fulfillment_progress(p),
        "slot_number": p.slot_number,
        "created_at": _iso(p.created_at),
    }


def email_to_dict(e: Email) -> dict:
    return {
        "id": str(e.id),
        "participation_id": str(e.participation_id),
        "version": e.version,
        "author": e.author,
        "subject": e.subject,
        "body": e.body,
        "status": e.status,
        "approved_at": _iso(e.approved_at),
        "sent_at": _iso(e.sent_at),
        "delivery_provider": e.delivery_provider,
        "provider_draft_id": e.provider_draft_id,
        "handed_off_at": _iso(e.handed_off_at),
        "created_at": _iso(e.created_at),
    }


def comment_to_dict(c: Comment) -> dict:
    return {
        "id": str(c.id),
        "entity_type": c.entity_type,
        "entity_id": str(c.entity_id),
        "slot_number": c.slot_number,
        "author": c.author,
        "body": c.body,
        "resolved": c.resolved,
        "created_at": _iso(c.created_at),
    }


def activity_to_dict(a: AgentActivity) -> dict:
    return {
        "id": str(a.id),
        "tool_name": a.tool_name,
        "args_summary": a.args_summary,
        "outcome": a.outcome,
        "detail": a.detail,
        "created_at": _iso(a.created_at),
    }


def postcard_draft_to_dict(d: PostcardDraft) -> dict:
    return {
        "id": str(d.id),
        "campaign_id": str(d.campaign_id),
        "version": d.version,
        "template_id": d.template_id,
        "slots": d.slots,
        "notes": d.notes,
        "created_at": _iso(d.created_at),
    }
