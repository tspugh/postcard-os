from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from server.errors import Conflict, NotFound, ValidationRejected
from server.models import Business, CAMPAIGN_STATUSES, Campaign, Participation
from server.services.serialize import business_to_dict, campaign_to_dict, participation_to_dict
from server.services.settings import get_settings

ACTIVE_CAMPAIGN_STATUSES = ("draft", "filling", "full", "fulfillment")


def get_campaign(session: Session, campaign_id) -> Campaign:
    c = session.get(Campaign, campaign_id)
    if c is None:
        raise NotFound(f"No campaign with id {campaign_id}.")
    return c


def active_campaign(session: Session) -> Campaign | None:
    return session.scalars(
        select(Campaign)
        .where(Campaign.status.in_(ACTIVE_CAMPAIGN_STATUSES))
        .order_by(Campaign.created_at.desc())
    ).first()


def create_campaign(
    session: Session,
    month: date,
    deadline: date,
    name: str | None = None,
    market: str | None = None,
) -> dict:
    s = get_settings(session)
    market = (market or s.seed_market).strip()
    name = (name or f"{market} {month.strftime('%B %Y')}").strip()
    c = Campaign(
        name=name,
        market=market,
        month=month,
        deadline=deadline,
        slot_price_cents=s.default_slot_price_cents,
        total_slots=s.default_total_slots,
    )
    session.add(c)
    session.flush()
    return campaign_to_dict(c)


def list_campaigns(session: Session) -> list[dict]:
    return [campaign_to_dict(c) for c in session.scalars(select(Campaign).order_by(Campaign.created_at.desc()))]


def set_campaign_status(session: Session, campaign_id, status: str) -> dict:
    c = get_campaign(session, campaign_id)
    if status not in CAMPAIGN_STATUSES:
        raise ValidationRejected(f"'{status}' is not a campaign status. Valid: {', '.join(CAMPAIGN_STATUSES)}.")
    if c.status == "archived" and status != "completed":
        raise Conflict(
            "An archived campaign can only be unarchived back to 'completed' (operator action). "
            "Campaigns are archived, never deleted."
        )
    c.status = status
    session.flush()
    return campaign_to_dict(c)


def priority_prospects(session: Session, campaign_id) -> list[dict]:
    """Waitlisted (and committed/paid from completed runs) businesses in *other* campaigns
    for the same market — preserved revenue surfaced when composing the next campaign."""
    c = get_campaign(session, campaign_id)
    rows = session.execute(
        select(Participation, Campaign, Business)
        .join(Campaign, Participation.campaign_id == Campaign.id)
        .join(Business, Participation.business_id == Business.id)
        .where(
            Campaign.market == c.market,
            Campaign.id != c.id,
            Business.status != "disqualified",
        )
        .order_by(Participation.created_at.desc())
    ).all()
    already_attached = {
        p.business_id for p in session.scalars(select(Participation).where(Participation.campaign_id == c.id))
    }
    out, seen = [], set()
    for p, prior, b in rows:
        if b.id in seen or b.id in already_attached:
            continue
        if p.status == "waitlisted":
            reason = f"waitlisted in '{prior.name}' (position {p.waitlist_order})"
        elif p.status in ("committed", "paid") and prior.status in ("completed", "archived"):
            reason = f"participated in '{prior.name}'"
        else:
            continue
        seen.add(b.id)
        out.append({"business": business_to_dict(b, include_contacts=False), "reason": reason, "prior_participation": participation_to_dict(p, business_name=b.name)})
    return out
