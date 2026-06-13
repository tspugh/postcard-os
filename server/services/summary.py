"""Orientation and roll-up documents. MCP's get_campaign_status and the dashboard's
composite endpoints both read from here — one source for every number on screen."""

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from server.models import Business, Campaign, Comment, Contact, Email, Participation
from server.services import campaigns as campaign_service
from server.services.serialize import campaign_to_dict, fulfillment_progress, participation_to_dict
from server.services.settings import get_settings, settings_to_dict


def _campaign_board(session: Session, campaign: Campaign) -> dict:
    settings = get_settings(session)
    parts = list(
        session.scalars(select(Participation).where(Participation.campaign_id == campaign.id))
    )
    business_names = {
        b.id: b.name
        for b in session.scalars(select(Business).where(Business.id.in_([p.business_id for p in parts])))
    } if parts else {}

    categories = list(dict.fromkeys(list(settings.categories) + [p.category for p in parts]))
    slots = []
    for cat in categories:
        cat_parts = [p for p in parts if p.category == cat]
        committed = next((p for p in cat_parts if p.status in ("committed", "paid")), None)
        waitlist = sorted((p for p in cat_parts if p.status == "waitlisted"), key=lambda p: p.waitlist_order or 0)
        pitched = [p for p in cat_parts if p.status in ("prospecting", "contacted", "interested")]
        slots.append(
            {
                "category": cat,
                "state": "committed" if committed else ("pitched" if pitched else "empty"),
                "committed": (
                    {
                        "participation_id": str(committed.id),
                        "business_name": business_names.get(committed.business_id),
                        "amount_cents": committed.committed_amount_cents,
                        "payment_status": committed.payment_status,
                        "slot_number": committed.slot_number,
                        "fulfillment_progress": fulfillment_progress(committed),
                    }
                    if committed
                    else None
                ),
                "pitched_count": len(pitched),
                "waitlist": [
                    participation_to_dict(p, business_name=business_names.get(p.business_id)) for p in waitlist
                ],
            }
        )

    committed_parts = [p for p in parts if p.status in ("committed", "paid")]
    filled = len(committed_parts)
    days_remaining = (campaign.deadline - date.today()).days

    from server.services.documents import EMPTY_EMAIL_ROLLUP, _business_comment_counts, _email_rollup

    rollups = _email_rollup(session, [p.id for p in parts])
    biz_comments = _business_comment_counts(session, [p.business_id for p in parts])
    participations = [
        {
            **participation_to_dict(p, business_name=business_names.get(p.business_id)),
            **(rollups.get(p.id) or EMPTY_EMAIL_ROLLUP),
            "business_unresolved_comments": biz_comments.get(p.business_id, 0),
        }
        for p in sorted(parts, key=lambda p: p.created_at, reverse=True)
    ]

    # Drafts whose operator feedback is newer than the agent's latest version — the
    # agent's revision worklist. Subject/body included so the agent revises against the
    # actual current draft, not just the operator's reaction to it.
    needs_revision = {
        p.id: r for p in parts for r in [rollups.get(p.id)]
        if r and r["email_state"] == "revisions_requested"
    }
    current_emails = {
        str(e.id): e
        for e in session.scalars(
            select(Email).where(Email.id.in_([r["current_email_id"] for r in needs_revision.values()]))
        )
    } if needs_revision else {}
    revision_requests = [
        {
            "participation_id": str(pid),
            "business_name": business_names.get(next(p.business_id for p in parts if p.id == pid)),
            "category": next(p.category for p in parts if p.id == pid),
            "email_id": r["current_email_id"],
            "version": r["current_version"],
            "subject": current_emails[r["current_email_id"]].subject if r["current_email_id"] in current_emails else None,
            "body": current_emails[r["current_email_id"]].body if r["current_email_id"] in current_emails else None,
            "unresolved_comments": r["unresolved_feedback"],
        }
        for pid, r in needs_revision.items()
    ]

    # Approved versions not yet handed into the operator's mailbox as drafts — the
    # agent's mail-handoff worklist (subject/body included so the handoff is verbatim).
    parts_by_id = {p.id: p for p in parts}
    pending = list(
        session.scalars(
            select(Email)
            .where(
                Email.participation_id.in_(parts_by_id.keys()),
                Email.status == "approved",
                Email.provider_draft_id.is_(None),
            )
            .order_by(Email.approved_at)
        )
    ) if parts else []
    primary_emails: dict = {}
    if pending:
        recipients = session.scalars(
            select(Contact).where(
                Contact.business_id.in_({parts_by_id[e.participation_id].business_id for e in pending}),
                Contact.email.is_not(None),
            )
        )
        for c in recipients:
            if c.is_primary or c.business_id not in primary_emails:
                primary_emails[c.business_id] = {"to": c.email, "to_name": c.name}
    approved_awaiting_handoff = [
        {
            "email_id": str(e.id),
            "participation_id": str(e.participation_id),
            "business_name": business_names.get(parts_by_id[e.participation_id].business_id),
            "category": parts_by_id[e.participation_id].category,
            **primary_emails.get(parts_by_id[e.participation_id].business_id, {"to": None, "to_name": None}),
            "version": e.version,
            "subject": e.subject,
            "body": e.body,
            "approved_at": e.approved_at.isoformat() if e.approved_at else None,
        }
        for e in pending
    ]

    return {
        "campaign": campaign_to_dict(campaign),
        "slots": slots,
        "participations": participations,
        "approved_awaiting_handoff": approved_awaiting_handoff,
        "revision_requests": revision_requests,
        "slots_filled": filled,
        "slots_total": campaign.total_slots,
        "scarcity": f"{filled} of {campaign.total_slots} filled, closes {campaign.deadline.isoformat()}",
        "days_until_deadline": days_remaining,
        "waitlist_count": sum(1 for p in parts if p.status == "waitlisted"),
        "committed_cents": sum(p.committed_amount_cents or 0 for p in committed_parts),
        "collected_cents": sum(
            p.committed_amount_cents or 0 for p in committed_parts if p.payment_status == "paid"
        ),
        "participation_counts": {
            status: sum(1 for p in parts if p.status == status)
            for status in ("prospecting", "contacted", "interested", "waitlisted", "committed", "paid", "declined")
        },
        "ready_to_print": filled == campaign.total_slots
        and all(fulfillment_progress(p) == "3/3" for p in committed_parts),
    }


def campaign_board(session: Session, campaign_id) -> dict:
    return _campaign_board(session, campaign_service.get_campaign(session, campaign_id))


def open_feedback(session: Session) -> list[dict]:
    """Every unresolved operator comment on a business or an email, with context — the
    agent's cross-cutting feedback list. Resolving a comment (operator action) is what
    removes it here; the agent never resolves."""
    comments = list(
        session.scalars(
            select(Comment)
            .where(Comment.resolved.is_(False), Comment.entity_type.in_(("business", "email")))
            .order_by(Comment.created_at)
        )
    )
    if not comments:
        return []
    email_ids = [c.entity_id for c in comments if c.entity_type == "email"]
    emails = {
        e.id: e for e in session.scalars(select(Email).where(Email.id.in_(email_ids)))
    } if email_ids else {}
    part_ids = {e.participation_id for e in emails.values()}
    parts = {
        p.id: p for p in session.scalars(select(Participation).where(Participation.id.in_(part_ids)))
    } if part_ids else {}
    biz_ids = {c.entity_id for c in comments if c.entity_type == "business"} | {
        p.business_id for p in parts.values()
    }
    bizes = {
        b.id: b for b in session.scalars(select(Business).where(Business.id.in_(biz_ids)))
    } if biz_ids else {}

    out = []
    for c in comments:
        item = {
            "comment_id": str(c.id),
            "entity_type": c.entity_type,
            "entity_id": str(c.entity_id),
            "author": c.author,
            "body": c.body,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        if c.entity_type == "email":
            e = emails.get(c.entity_id)
            p = parts.get(e.participation_id) if e else None
            item.update(
                {
                    "email_version": e.version if e else None,
                    "email_status": e.status if e else None,
                    "participation_id": str(e.participation_id) if e else None,
                    "business_id": str(p.business_id) if p else None,
                    "business_name": bizes[p.business_id].name if p and p.business_id in bizes else None,
                }
            )
        else:
            b = bizes.get(c.entity_id)
            item.update({"business_id": str(c.entity_id), "business_name": b.name if b else None})
        out.append(item)
    return out


def get_campaign_status(session: Session, campaign_id=None) -> dict:
    """The agent's one-call orientation: campaign + fill map + ordered waitlists +
    pipeline counts + settings (price, categories, market, sender, instructions) inline."""
    settings = get_settings(session)
    campaign = (
        campaign_service.get_campaign(session, campaign_id)
        if campaign_id
        else campaign_service.active_campaign(session)
    )
    pipeline_counts = dict(
        session.execute(select(Business.status, func.count()).group_by(Business.status)).all()
    )
    doc = {
        "settings": settings_to_dict(settings),
        "pipeline_counts": {
            status: pipeline_counts.get(status, 0)
            for status in ("staged", "researching", "researched", "disqualified")
        },
        "campaign_board": _campaign_board(session, campaign) if campaign else None,
        "open_feedback": open_feedback(session),
    }
    ob = settings.operator_business or {}
    if not ob.get("signature") or not ob.get("name"):
        doc["warnings"] = [
            "The sender profile/signature in settings is incomplete — drafts cannot be "
            "signed per the email expectations. Ask the operator to fill in Settings → "
            "My business before drafting more outreach."
        ]
    if campaign is None:
        doc["note"] = (
            "No active campaign. Tell the operator to create one in the dashboard so you can "
            "attach businesses and draft outreach — or, ONLY if the operator has explicitly "
            "asked you for a new campaign, create it with postcard_create_campaign. You can "
            "always stage and research leads — they attach to a campaign later."
        )
    return doc


def summary_strip(session: Session) -> dict:
    """Dashboard home: 'what needs attention today' in one row of numbers."""
    campaign = campaign_service.active_campaign(session)
    drafts_awaiting = session.scalar(
        select(func.count()).select_from(Email).where(Email.status == "in_review")
    )
    unviewed = session.scalar(
        select(func.count())
        .select_from(Business)
        .where(Business.operator_viewed_at.is_(None), Business.status != "disqualified")
    )
    out = {
        "drafts_awaiting_review": drafts_awaiting,
        "unviewed_businesses": unviewed,
        "campaign": None,
    }
    if campaign is not None:
        board = _campaign_board(session, campaign)
        out["campaign"] = {
            "id": str(campaign.id),
            "name": campaign.name,
            "status": campaign.status,
            "slots_filled": board["slots_filled"],
            "slots_total": board["slots_total"],
            "scarcity": board["scarcity"],
            "days_until_deadline": board["days_until_deadline"],
            "waitlist_count": board["waitlist_count"],
            "committed_cents": board["committed_cents"],
            "collected_cents": board["collected_cents"],
        }
    return out
