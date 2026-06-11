import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from server.config import CLAIM_TTL_SECONDS
from server.errors import Conflict, NotFound, ValidationRejected
from server.models import (
    ACTIVE_PARTICIPATION_STATUSES,
    Business,
    Campaign,
    Contact,
    DQ_REASON_CODES,
    Participation,
)
from server.services.contacts import validate_contact_payload
from server.services.serialize import business_to_dict

STAGING_BAR = (
    "Staging bar: a lead needs a business name, a category tag, and a working website URL "
    "(site, Google Business profile, or active social page — proof the business exists). "
    "Email is not required at staging; finding contacts is research work."
)

RESEARCH_BAR = (
    "Research bar: at least one contact with an email or phone (email needs a source and a "
    "confidence of listed/scraped/guessed), a premise (2-3 factual sentences: what the business "
    "does and for whom), at least one hook (specific personalization ammunition), and at least "
    "one evidence URL."
)


def _now():
    return datetime.now(timezone.utc)


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def get_business(session: Session, business_id) -> Business:
    b = session.get(Business, business_id)
    if b is None:
        raise NotFound(f"No business with id {business_id}. Use postcard_list_staged_leads or the pipeline board to find valid ids.")
    return b


def active_participations(session: Session, business_id) -> list[Participation]:
    return list(
        session.scalars(
            select(Participation).where(
                Participation.business_id == business_id,
                Participation.status.in_(ACTIVE_PARTICIPATION_STATUSES),
            )
        )
    )


def stage_leads(session: Session, leads: list[dict], source: str = "agent:web") -> dict:
    """Bulk staging. Enforces the staging bar per lead; dedupes by normalized name.
    Returns {staged: [...], rejected: [{lead, reason}]} — one bad lead never sinks the batch."""
    existing = {
        _normalize_name(name): (bid, name, status, dq_code)
        for bid, name, status, dq_code in session.execute(
            select(Business.id, Business.name, Business.status, Business.dq_code)
        )
    }
    staged, rejected = [], []
    for lead in leads:
        name = (lead.get("name") or "").strip()
        category = (lead.get("category") or "").strip().lower()
        website = (lead.get("website") or "").strip()
        missing = [f for f, v in (("name", name), ("category", category), ("website", website)) if not v]
        if missing:
            rejected.append({"lead": lead, "reason": f"Missing {', '.join(missing)}. {STAGING_BAR}"})
            continue
        if "." not in website:
            rejected.append({"lead": lead, "reason": f"'{website}' does not look like a URL. {STAGING_BAR}"})
            continue
        if not re.match(r"^https?://", website):
            website = "https://" + website
        key = _normalize_name(name)
        if key in existing:
            _, ex_name, ex_status, ex_dq = existing[key]
            if ex_status == "disqualified":
                reason = (
                    f"'{name}' matches '{ex_name}', which was disqualified ({ex_dq}). "
                    "Disqualified leads are never re-staged or re-researched."
                )
            else:
                reason = (
                    f"'{name}' duplicates existing record '{ex_name}' (status: {ex_status}). "
                    "Duplicates are never merged automatically; work the existing record instead."
                )
            rejected.append({"lead": lead, "reason": reason})
            continue
        b = Business(name=name, category=category, website=website, source=source, status="staged")
        if lead.get("note"):
            b.premise = None  # notes are not premises; keep the bar honest
        session.add(b)
        session.flush()
        existing[key] = (b.id, b.name, b.status, None)
        staged.append(business_to_dict(b, include_contacts=False))
    return {"staged": staged, "rejected": rejected}


def list_staged(session: Session, limit: int = 50) -> list[dict]:
    rows = session.scalars(
        select(Business)
        .where(Business.status == "staged")
        .order_by(Business.created_at)
        .limit(limit)
    )
    return [business_to_dict(b, include_contacts=False) for b in rows]


def list_businesses(session: Session, status: str | None = None) -> list[dict]:
    q = select(Business).order_by(Business.created_at.desc())
    if status:
        q = q.where(Business.status == status)
    return [business_to_dict(b) for b in session.scalars(q)]


def claim_lead(session: Session, business_id) -> dict:
    b = get_business(session, business_id)
    if b.status == "disqualified":
        raise Conflict(
            f"'{b.name}' is disqualified ({b.dq_code}) — disqualified leads are never re-researched. "
            "Pick another lead from postcard_list_staged_leads."
        )
    if b.status == "researching":
        stale = b.claimed_at is None or (_now() - b.claimed_at) > timedelta(seconds=CLAIM_TTL_SECONDS)
        if not stale:
            raise Conflict(
                f"'{b.name}' is already claimed (researching, claimed at {b.claimed_at.isoformat()}). "
                "Claims expire after 1 hour; pick another staged lead meanwhile."
            )
    elif b.status != "staged":
        raise Conflict(
            f"'{b.name}' is in state '{b.status}', not 'staged'. Only staged leads can be claimed; "
            "use postcard_list_staged_leads to find one."
        )
    b.status = "researching"
    b.claimed_at = _now()
    session.flush()
    return business_to_dict(b)


def submit_research(session: Session, business_id, research: dict) -> dict:
    b = get_business(session, business_id)
    if b.status != "researching":
        hint = "Claim it first with postcard_claim_lead." if b.status == "staged" else f"Current state: '{b.status}'."
        raise Conflict(f"Research can only be submitted for a lead you are researching. {hint}")

    premise = (research.get("premise") or "").strip()
    hooks = [h.strip() for h in (research.get("hooks") or []) if isinstance(h, str) and h.strip()]
    evidence_urls = [u.strip() for u in (research.get("evidence_urls") or []) if isinstance(u, str) and u.strip()]
    contacts = research.get("contacts") or []

    problems = []
    if not premise:
        problems.append("premise is missing")
    if not hooks:
        problems.append("at least one hook is required")
    if not evidence_urls:
        problems.append("at least one evidence URL is required")
    if not contacts:
        problems.append("at least one contact with an email or phone is required")
    for i, c in enumerate(contacts):
        err = validate_contact_payload(c)
        if err:
            problems.append(f"contact[{i}]: {err}")
    if problems:
        raise ValidationRejected(f"Research rejected — {'; '.join(problems)}. {RESEARCH_BAR}")

    b.premise = premise
    b.hooks = hooks
    b.evidence_urls = evidence_urls
    b.status = "researched"
    b.claimed_at = None
    has_primary = any(c.get("is_primary") for c in contacts)
    for i, c in enumerate(contacts):
        session.add(
            Contact(
                business_id=b.id,
                name=c.get("name"),
                title=c.get("title"),
                email=c.get("email"),
                email_source=c.get("email_source"),
                email_confidence=c.get("email_confidence"),
                phone=c.get("phone"),
                is_primary=bool(c.get("is_primary")) or (not has_primary and i == 0),
            )
        )
    session.flush()
    session.refresh(b)
    return business_to_dict(b)


UPDATABLE_FIELDS = {"address", "service_area", "premise", "hooks", "evidence_urls", "category"}


def update_business(session: Session, business_id, fields: dict) -> dict:
    b = get_business(session, business_id)
    if b.status == "disqualified":
        raise Conflict(f"'{b.name}' is disqualified; disqualified records are read-only.")
    unknown = set(fields) - UPDATABLE_FIELDS
    if unknown:
        raise ValidationRejected(
            f"Cannot update fields {sorted(unknown)}. Updatable fields: {sorted(UPDATABLE_FIELDS)}. "
            "Contacts have their own tools (postcard_save_contact / postcard_delete_contact)."
        )
    if "category" in fields and not (fields["category"] or "").strip():
        raise ValidationRejected("category cannot be emptied; every business carries a category tag.")
    for key, value in fields.items():
        setattr(b, key, value.strip().lower() if key == "category" else value)
    session.flush()
    return business_to_dict(b)


def disqualify(session: Session, business_id, dq_code: str, reason: str | None = None) -> dict:
    b = get_business(session, business_id)
    if dq_code not in DQ_REASON_CODES:
        raise ValidationRejected(
            f"'{dq_code}' is not a disqualification code. Valid codes: {', '.join(DQ_REASON_CODES)}."
        )
    if dq_code == "other" and not (reason or "").strip():
        raise ValidationRejected("Code 'other' requires a free-text reason explaining the disqualification.")
    if b.status == "disqualified":
        raise Conflict(f"'{b.name}' is already disqualified ({b.dq_code}).")
    actives = active_participations(session, b.id)
    if actives:
        p = actives[0]
        campaign = session.get(Campaign, p.campaign_id)
        raise Conflict(
            f"Cannot disqualify '{b.name}' — it has an active participation ({p.status}) in campaign "
            f"'{campaign.name}'. Active advertisers (prospecting through paid) are protected; "
            "the operator must decline the participation first."
        )
    b.status = "disqualified"
    b.dq_code = dq_code
    b.dq_reason = (reason or "").strip() or None
    b.claimed_at = None
    session.flush()
    return business_to_dict(b)


def mark_viewed(session: Session, business_id) -> dict:
    """Operator opened the detail view — clears the 'unviewed' badge."""
    b = get_business(session, business_id)
    if b.operator_viewed_at is None:
        b.operator_viewed_at = _now()
        session.flush()
    return business_to_dict(b)
