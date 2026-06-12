"""Orientation and roll-up documents. MCP's get_campaign_status and the dashboard's
composite endpoints both read from here — one source for every number on screen."""

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from server.models import Business, Campaign, Email, Participation
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

    from server.services.documents import _drafts_in_review

    drafts_by_part = _drafts_in_review(session, [p.id for p in parts])
    participations = [
        {
            **participation_to_dict(p, business_name=business_names.get(p.business_id)),
            "drafts_in_review": drafts_by_part.get(p.id, 0),
        }
        for p in sorted(parts, key=lambda p: p.created_at, reverse=True)
    ]

    return {
        "campaign": campaign_to_dict(campaign),
        "slots": slots,
        "participations": participations,
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
    }
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
