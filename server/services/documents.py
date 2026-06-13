"""Composite UI documents — each dashboard view hydrates from ONE endpoint returning
one JSON document (TRD §1, MCP-app readiness). Built on the same serializers as MCP."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from server.models import Business, Campaign, Comment, Email, Interaction, Participation
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
    if i.type == "mail_draft_handed_off":
        return f"Placed in {p.get('provider', 'mailbox')} drafts by agent — “{p.get('subject', '')}”"
    if i.type == "comment_added":
        who = "Agent" if p.get("author") == "agent" else "Grant"
        where = f" on email v{p['email_version']}" if p.get("email_version") else ""
        body = (p.get("body") or "").strip()
        return f"{who} commented{where} — “{body[:80]}{'…' if len(body) > 80 else ''}”"
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


EMPTY_EMAIL_ROLLUP = {
    "drafts_in_review": 0,
    "email_state": None,
    "current_email_id": None,
    "current_version": None,
    "unresolved_feedback": 0,
}


def _email_rollup(session: Session, participation_ids: list) -> dict:
    """Per-participation derived display state for how far the outreach email is along:
    None → draft_in_review → revisions_requested ⇄ revised → approved → in_mailbox → sent.
    Deliberately NOT a stored participation status — drafting lives on the email thread;
    the participation only advances (to contacted) when a send actually happens.

    The revision sub-states compare timestamps: unresolved operator comments newer than
    the current in-review version mean the agent owes a revision (revisions_requested);
    an in-review version newer than the latest unresolved comment means the agent has
    responded and the operator should re-review (revised)."""
    if not participation_ids:
        return {}
    emails = list(session.scalars(select(Email).where(Email.participation_id.in_(participation_ids))))
    if not emails:
        return {}
    unresolved_by_email: dict = {}
    for c in session.scalars(
        select(Comment).where(
            Comment.entity_type == "email",
            Comment.entity_id.in_([e.id for e in emails]),
            Comment.resolved.is_(False),
        )
    ):
        unresolved_by_email.setdefault(c.entity_id, []).append(c)

    by_part: dict = {}
    for e in emails:
        by_part.setdefault(e.participation_id, []).append(e)

    out: dict = {}
    for pid, thread in by_part.items():
        in_review = [e for e in thread if e.status == "in_review"]
        current = max(in_review, key=lambda e: e.version) if in_review else None
        approved = max((e for e in thread if e.status == "approved"), key=lambda e: e.version, default=None)
        feedback = [c for e in thread for c in unresolved_by_email.get(e.id, [])]
        latest_feedback = max((c.created_at for c in feedback), default=None)
        if current is not None:
            if latest_feedback is None:
                state = "draft_in_review"
            elif current.created_at > latest_feedback:
                state = "revised"
            else:
                state = "revisions_requested"
        elif approved is not None:
            state = "in_mailbox" if approved.provider_draft_id else "approved"
        elif any(e.status == "sent" for e in thread):
            state = "sent"
        else:
            state = None
        out[pid] = {
            "drafts_in_review": len(in_review),
            "email_state": state,
            "current_email_id": str(current.id) if current else None,
            "current_version": current.version if current else None,
            "unresolved_feedback": len(feedback),
        }
    return out


def _business_comment_counts(session: Session, business_ids: list) -> dict:
    """Unresolved business-level comments per business — the card-badge counterpart to
    the per-participation email feedback in _email_rollup."""
    if not business_ids:
        return {}
    rows = session.execute(
        select(Comment.entity_id, func.count())
        .where(
            Comment.entity_type == "business",
            Comment.entity_id.in_(business_ids),
            Comment.resolved.is_(False),
        )
        .group_by(Comment.entity_id)
    ).all()
    return {bid: n for bid, n in rows}


def _participation_doc(session: Session, p: Participation, campaign: Campaign, rollup: dict | None) -> dict:
    rollup = rollup or EMPTY_EMAIL_ROLLUP
    return {
        **participation_to_dict(p),
        "campaign": campaign_to_dict(campaign),
        "drafts_in_review": rollup["drafts_in_review"],
        "email_state": rollup["email_state"],
        "unresolved_feedback": rollup["unresolved_feedback"],
    }


def list_business_documents(session: Session) -> list[dict]:
    """Leads view: every business with its most relevant participation (active campaign
    first, then most recent) and a drafts-in-review count."""
    businesses = list(session.scalars(select(Business).order_by(Business.created_at.desc())))
    parts = list(session.scalars(select(Participation)))
    campaigns = {c.id: c for c in session.scalars(select(Campaign))}
    rollups = _email_rollup(session, [p.id for p in parts])
    biz_comments = _business_comment_counts(session, [b.id for b in businesses])

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
        doc["unresolved_comments"] = biz_comments.get(b.id, 0)
        plist = by_business.get(b.id)
        doc["participation"] = (
            _participation_doc(session, best(plist), campaigns[best(plist).campaign_id], rollups.get(best(plist).id))
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
    rollups = _email_rollup(session, [p.id for p in parts])
    part_docs = []
    for p in parts:
        campaign = session.get(Campaign, p.campaign_id)
        pdoc = _participation_doc(session, p, campaign, rollups.get(p.id))
        pdoc["emails"] = [
            {**email_to_dict(e), "comments": list_comments(session, "email", e.id)}
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
