from datetime import datetime, timezone

from sqlalchemy import delete as sql_delete, func, select
from sqlalchemy.orm import Session

from server.errors import Conflict, NotFound, ValidationRejected
from server.models import (
    Business,
    Campaign,
    Comment,
    Email,
    FULFILLMENT_KEYS,
    FULFILLMENT_CHECKLIST_KEYS,
    Interaction,
    Participation,
)
from server.services.campaigns import get_campaign
from server.services.serialize import participation_to_dict

PAYMENT_METHODS = ("cash", "paypal", "check", "other")
PAYMENT_STATUSES = ("pending", "paid")


def _now():
    return datetime.now(timezone.utc)


def get_participation(session: Session, participation_id) -> Participation:
    p = session.get(Participation, participation_id)
    if p is None:
        raise NotFound(f"No participation with id {participation_id}.")
    return p


def _log(session: Session, p: Participation, type_: str, payload: dict | None = None):
    session.add(
        Interaction(
            business_id=p.business_id,
            participation_id=p.id,
            type=type_,
            payload=payload,
            occurred_at=_now(),
        )
    )


def _committed_holder(session: Session, campaign_id, category: str) -> Participation | None:
    return session.scalars(
        select(Participation).where(
            Participation.campaign_id == campaign_id,
            Participation.category == category,
            Participation.status.in_(("committed", "paid")),
        )
    ).first()


def _assign_slot(session: Session, campaign: Campaign) -> int:
    used = set(
        session.scalars(
            select(Participation.slot_number).where(
                Participation.campaign_id == campaign.id,
                Participation.status.in_(("committed", "paid")),
                Participation.slot_number.is_not(None),
            )
        )
    )
    for n in range(1, campaign.total_slots + 1):
        if n not in used:
            return n
    raise Conflict(
        f"All {campaign.total_slots} slots on '{campaign.name}' are committed — the card is full. "
        "Recommend postcard_move_to_waitlist so this demand carries into the next campaign."
    )


def _refresh_campaign_fill(session: Session, campaign: Campaign):
    committed = session.scalar(
        select(func.count()).select_from(Participation).where(
            Participation.campaign_id == campaign.id,
            Participation.status.in_(("committed", "paid")),
        )
    )
    if campaign.status == "draft" and committed > 0:
        campaign.status = "filling"
    if campaign.status == "filling" and committed >= campaign.total_slots:
        campaign.status = "full"
    elif campaign.status == "full" and committed < campaign.total_slots:
        campaign.status = "filling"
    session.flush()


def _renumber_waitlist(session: Session, campaign_id, category: str):
    """Keep waitlist_order dense (1..n). Two-phase to dodge the partial unique index."""
    rows = list(
        session.scalars(
            select(Participation)
            .where(
                Participation.campaign_id == campaign_id,
                Participation.category == category,
                Participation.status == "waitlisted",
            )
            .order_by(Participation.waitlist_order)
        )
    )
    for i, row in enumerate(rows):
        row.waitlist_order = -(i + 1)
    session.flush()
    for row in rows:
        row.waitlist_order = -row.waitlist_order
    session.flush()


def add_to_campaign(session: Session, campaign_id, business_id, category: str | None = None) -> dict:
    campaign = get_campaign(session, campaign_id)
    if campaign.status in ("completed", "archived"):
        raise Conflict(f"Campaign '{campaign.name}' is {campaign.status}; attach businesses to an active campaign.")
    b = session.get(Business, business_id)
    if b is None:
        raise NotFound(f"No business with id {business_id}.")
    if b.status != "researched":
        hint = {
            "staged": "Claim it (postcard_claim_lead) and submit research first.",
            "researching": "Submit research first (postcard_submit_research).",
            "disqualified": "Disqualified leads are never pitched.",
        }[b.status]
        raise Conflict(f"'{b.name}' is '{b.status}', not 'researched' — only researched businesses join a campaign. {hint}")
    existing = session.scalars(
        select(Participation).where(
            Participation.campaign_id == campaign.id, Participation.business_id == b.id
        )
    ).first()
    if existing is not None:
        raise Conflict(
            f"'{b.name}' already has participation {existing.id} (status '{existing.status}') in '{campaign.name}'."
        )
    p = Participation(
        campaign_id=campaign.id,
        business_id=b.id,
        category=(category or b.category).strip().lower(),
        asking_price_cents=campaign.slot_price_cents,
    )
    session.add(p)
    session.flush()
    _log(session, p, "attached_to_campaign", {"campaign": campaign.name, "asking_price_cents": p.asking_price_cents})
    return participation_to_dict(p, business_name=b.name)


def remove_from_campaign(session: Session, participation_id) -> dict:
    p = get_participation(session, participation_id)
    if p.status not in ("prospecting", "contacted"):
        raise Conflict(
            f"Participation is '{p.status}' — detaching is allowed only in prospecting or contacted. "
            "Past that point the relationship is history: decline it instead (operator action)."
        )
    email_ids = list(session.scalars(select(Email.id).where(Email.participation_id == p.id)))
    if email_ids:
        session.execute(
            sql_delete(Comment).where(Comment.entity_type == "email", Comment.entity_id.in_(email_ids))
        )
        session.execute(sql_delete(Email).where(Email.participation_id == p.id))
    session.execute(
        sql_delete(Interaction).where(Interaction.participation_id == p.id)
    )
    session.delete(p)
    session.flush()
    return {"removed": str(participation_id)}


def record_commitment(session: Session, participation_id, amount_cents: int) -> dict:
    p = get_participation(session, participation_id)
    if not isinstance(amount_cents, int) or amount_cents <= 0:
        raise ValidationRejected("A commitment needs a positive amount_cents (the negotiated number, in cents).")
    if p.status in ("committed", "paid"):
        raise Conflict(f"Participation is already '{p.status}' (amount {p.committed_amount_cents}).")
    if p.status == "waitlisted":
        raise Conflict(
            "Waitlisted participations are promoted by the operator (REST /promote), not committed directly — "
            "promotion re-checks exclusivity and keeps the waitlist fair."
        )
    if p.status == "declined":
        raise Conflict("This participation was declined. Re-attach the business to the campaign to pitch again.")
    campaign = get_campaign(session, p.campaign_id)
    holder = _committed_holder(session, p.campaign_id, p.category)
    if holder is not None:
        holder_business = session.get(Business, holder.business_id)
        raise Conflict(
            f"Category '{p.category}' on '{campaign.name}' is already won by '{holder_business.name}' "
            f"({holder.status}). One business per category per card. "
            "Call postcard_move_to_waitlist for this participation — waitlists preserve the revenue and "
            "carry forward to the next campaign."
        )
    p.slot_number = _assign_slot(session, campaign)
    p.committed_amount_cents = amount_cents
    p.status = "committed"
    p.payment_status = p.payment_status or "pending"
    session.flush()
    _log(session, p, "commitment_recorded", {"amount_cents": amount_cents, "slot_number": p.slot_number})
    _refresh_campaign_fill(session, campaign)
    return participation_to_dict(p)


def move_to_waitlist(session: Session, participation_id) -> dict:
    p = get_participation(session, participation_id)
    if p.status == "waitlisted":
        raise Conflict(f"Participation is already waitlisted at position {p.waitlist_order}.")
    if p.status not in ("prospecting", "contacted", "interested"):
        raise Conflict(
            f"Participation is '{p.status}' — only pre-commitment participations (prospecting, contacted, "
            "interested) move to the waitlist."
        )
    max_order = session.scalar(
        select(func.max(Participation.waitlist_order)).where(
            Participation.campaign_id == p.campaign_id,
            Participation.category == p.category,
            Participation.status == "waitlisted",
        )
    )
    p.status = "waitlisted"
    p.waitlist_order = (max_order or 0) + 1
    session.flush()
    _log(session, p, "waitlisted", {"position": p.waitlist_order})
    return participation_to_dict(p)


def promote_from_waitlist(session: Session, participation_id, amount_cents: int) -> dict:
    p = get_participation(session, participation_id)
    if p.status != "waitlisted":
        raise Conflict(f"Only waitlisted participations can be promoted; this one is '{p.status}'.")
    if not isinstance(amount_cents, int) or amount_cents <= 0:
        raise ValidationRejected("Promotion requires the committed amount_cents (promotion is a commitment).")
    holder = _committed_holder(session, p.campaign_id, p.category)
    if holder is not None:
        holder_business = session.get(Business, holder.business_id)
        raise Conflict(
            f"Category '{p.category}' is still occupied by '{holder_business.name}' ({holder.status}). "
            "Promotion is only possible when the slot is free (winner declined or detached)."
        )
    campaign = get_campaign(session, p.campaign_id)
    p.status = "committed"
    p.committed_amount_cents = amount_cents
    p.slot_number = _assign_slot(session, campaign)
    p.waitlist_order = None
    p.payment_status = p.payment_status or "pending"
    session.flush()
    _renumber_waitlist(session, p.campaign_id, p.category)
    _log(session, p, "waitlist_promoted", {"amount_cents": amount_cents, "slot_number": p.slot_number})
    _refresh_campaign_fill(session, campaign)
    return participation_to_dict(p)


def reorder_waitlist(session: Session, campaign_id, category: str, participation_ids: list) -> list[dict]:
    rows = list(
        session.scalars(
            select(Participation).where(
                Participation.campaign_id == campaign_id,
                Participation.category == category,
                Participation.status == "waitlisted",
            )
        )
    )
    current_ids = {str(r.id) for r in rows}
    given_ids = [str(i) for i in participation_ids]
    if current_ids != set(given_ids) or len(given_ids) != len(rows):
        raise ValidationRejected(
            f"Reorder must list every waitlisted participation for ({category}) exactly once. "
            f"Current waitlist: {sorted(current_ids)}."
        )
    by_id = {str(r.id): r for r in rows}
    for i, pid in enumerate(given_ids):
        by_id[pid].waitlist_order = -(i + 1)
    session.flush()
    for r in rows:
        r.waitlist_order = -r.waitlist_order
    session.flush()
    ordered = sorted(rows, key=lambda r: r.waitlist_order)
    return [participation_to_dict(r) for r in ordered]


def set_status(session: Session, participation_id, status: str) -> dict:
    """Operator state corrections (forward or backward, logged). Money/waitlist states
    must go through their dedicated flows so their invariants run."""
    p = get_participation(session, participation_id)
    if status == p.status:
        return participation_to_dict(p)
    if status == "committed":
        raise Conflict("Use the commitment flow (record_commitment / promote) — it checks exclusivity and assigns a slot.")
    if status == "waitlisted":
        raise Conflict("Use move_to_waitlist — it assigns the waitlist position.")
    if status == "paid":
        raise Conflict("Use the payment endpoint — paid requires payment method and date.")
    if status not in ("prospecting", "contacted", "interested", "declined"):
        raise ValidationRejected(f"'{status}' is not a settable status.")
    old = p.status
    was_waitlisted = p.status == "waitlisted"
    freed_slot = p.status in ("committed", "paid")
    p.status = status
    if status == "declined" or freed_slot or was_waitlisted:
        p.slot_number = None
        p.waitlist_order = None
    session.flush()
    if was_waitlisted:
        _renumber_waitlist(session, p.campaign_id, p.category)
    _log(session, p, "status_corrected", {"from": old, "to": status})
    if freed_slot:
        _refresh_campaign_fill(session, get_campaign(session, p.campaign_id))
    return participation_to_dict(p)


def record_payment(
    session: Session,
    participation_id,
    payment_status: str,
    payment_method: str | None = None,
    paid_at: datetime | None = None,
) -> dict:
    p = get_participation(session, participation_id)
    if p.status not in ("committed", "paid"):
        raise Conflict(
            f"Payment is recordable only on committed participations; this one is '{p.status}'. "
            "Record the commitment first."
        )
    if payment_status not in PAYMENT_STATUSES:
        raise ValidationRejected(f"payment_status must be one of {', '.join(PAYMENT_STATUSES)}.")
    if payment_method is not None and payment_method not in PAYMENT_METHODS:
        raise ValidationRejected(f"payment_method must be one of {', '.join(PAYMENT_METHODS)}.")
    p.payment_status = payment_status
    if payment_method is not None:
        p.payment_method = payment_method
    if payment_status == "paid":
        if p.payment_method is None:
            raise ValidationRejected(f"Marking paid requires a payment_method ({', '.join(PAYMENT_METHODS)}).")
        p.paid_at = paid_at or _now()
        p.status = "paid"
    session.flush()
    _log(session, p, "payment_recorded", {"payment_status": payment_status, "payment_method": p.payment_method})
    return participation_to_dict(p)


def update_fulfillment(session: Session, participation_id, fields: dict) -> dict:
    p = get_participation(session, participation_id)
    if p.status not in ("committed", "paid"):
        raise Conflict(
            f"The fulfillment checklist unlocks at 'committed'; this participation is '{p.status}'."
        )
    unknown = set(fields) - set(FULFILLMENT_KEYS)
    if unknown:
        raise ValidationRejected(f"Unknown fulfillment fields {sorted(unknown)}. Valid: {sorted(FULFILLMENT_KEYS)}.")
    for key in FULFILLMENT_CHECKLIST_KEYS:
        if key in fields and not isinstance(fields[key], bool):
            raise ValidationRejected(f"{key} must be a boolean.")
    p.fulfillment = {**(p.fulfillment or {}), **fields}
    session.flush()
    return participation_to_dict(p)


def get_thread(session: Session, participation_id) -> list[dict]:
    from server.services.serialize import email_to_dict

    get_participation(session, participation_id)
    rows = session.scalars(
        select(Email).where(Email.participation_id == participation_id).order_by(Email.version.desc())
    )
    return [email_to_dict(e) for e in rows]
