"""Composite UI documents — each dashboard view hydrates from ONE endpoint returning
one JSON document (TRD §1, MCP-app readiness). Built on the same serializers as MCP."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from server.models import Business, Campaign, Email, Interaction, Participation
from server.services import businesses as business_service
from server.services.campaigns import ACTIVE_CAMPAIGN_STATUSES
from server.services.comments import list_comments
from server.services.serialize import (
    business_to_dict,
    campaign_to_dict,
    email_to_dict,
    participation_to_dict,
)


def _money(cents):
    return "—" if cents is None else f"${cents / 100:,.0f}" if cents % 100 == 0 else f"${cents / 100:,.2f}"


def interaction_label(i: Interaction) -> str:
    """Humanize an interaction row for the drawer's 'State changes' list."""
    p = i.payload or {}
    if i.type == "attached_to_campaign":
        return f"Attached to {p.get('campaign', 'campaign')} · asking {_money(p.get('asking_price_cents'))} snapshotted"
    if i.type == "commitment_recorded":
        return f"Committed at {_money(p.get('amount_cents'))} · slot {p.get('slot_number', '?')} assigned"
    if i.type == "waitlisted":
        return f"Moved to waitlist #{p.get('position', '?')}"
    if i.type == "waitlist_promoted":
        return f"Promoted from waitlist at {_money(p.get('amount_cents'))} · slot {p.get('slot_number', '?')}"
    if i.type == "email_sent":
        return f"Marked sent by operator — “{p.get('subject', '')}”"
    if i.type == "payment_recorded":
        method = f" ({p.get('payment_method')})" if p.get("payment_method") else ""
        return f"Payment {p.get('payment_status', 'recorded')}{method}"
    if i.type == "status_corrected":
        return f"Status corrected: {p.get('from')} → {p.get('to')}"
    return i.type.replace("_", " ")


def interaction_to_dict(i: Interaction) -> dict:
    return {
        "id": str(i.id),
        "type": i.type,
        "label": interaction_label(i),
        "occurred_at": i.occurred_at.isoformat() if i.occurred_at else None,
    }


def _drafts_in_review(session: Session, participation_ids: list) -> dict:
    if not participation_ids:
        return {}
    rows = session.execute(
        select(Email.participation_id, func.count())
        .where(Email.participation_id.in_(participation_ids), Email.status == "in_review")
        .group_by(Email.participation_id)
    ).all()
    return {pid: n for pid, n in rows}


def _participation_doc(session: Session, p: Participation, campaign: Campaign, drafts: int) -> dict:
    return {
        **participation_to_dict(p),
        "campaign": campaign_to_dict(campaign),
        "drafts_in_review": drafts,
    }


def list_business_documents(session: Session) -> list[dict]:
    """Leads view: every business with its most relevant participation (active campaign
    first, then most recent) and a drafts-in-review count."""
    businesses = list(session.scalars(select(Business).order_by(Business.created_at.desc())))
    parts = list(session.scalars(select(Participation)))
    campaigns = {c.id: c for c in session.scalars(select(Campaign))}
    drafts = _drafts_in_review(session, [p.id for p in parts])

    by_business: dict = {}
    for p in parts:
        by_business.setdefault(p.business_id, []).append(p)

    def best(plist):
        def rank(p):
            c = campaigns[p.campaign_id]
            return (c.status in ACTIVE_CAMPAIGN_STATUSES, p.created_at)
        return max(plist, key=rank)

    out = []
    for b in businesses:
        doc = business_to_dict(b)
        plist = by_business.get(b.id)
        doc["participation"] = (
            _participation_doc(session, best(plist), campaigns[best(plist).campaign_id], drafts.get(best(plist).id, 0))
            if plist
            else None
        )
        out.append(doc)
    return out


def business_detail_document(session: Session, business_id) -> dict:
    """Drawer: business + contacts + comments + every participation with its campaign,
    full email thread (newest first), and humanized state changes. Marks viewed."""
    doc = business_service.mark_viewed(session, business_id)
    doc["comments"] = list_comments(session, "business", business_id)

    parts = list(
        session.scalars(
            select(Participation)
            .where(Participation.business_id == business_id)
            .order_by(Participation.created_at.desc())
        )
    )
    drafts = _drafts_in_review(session, [p.id for p in parts])
    part_docs = []
    for p in parts:
        campaign = session.get(Campaign, p.campaign_id)
        pdoc = _participation_doc(session, p, campaign, drafts.get(p.id, 0))
        pdoc["emails"] = [
            email_to_dict(e)
            for e in session.scalars(
                select(Email).where(Email.participation_id == p.id).order_by(Email.version.desc())
            )
        ]
        pdoc["events"] = [
            interaction_to_dict(i)
            for i in session.scalars(
                select(Interaction)
                .where(Interaction.participation_id == p.id)
                .order_by(Interaction.occurred_at.desc())
            )
        ]
        part_docs.append(pdoc)
    doc["participations"] = part_docs
    return doc
