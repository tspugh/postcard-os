from datetime import datetime, timezone

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from server.errors import Conflict, NotFound, ValidationRejected
from server.models import (
    EMAIL_AUTHORS,
    EMAIL_STATUSES,
    MAIL_PROVIDERS,
    Business,
    Comment,
    Email,
    Interaction,
    Participation,
)
from server.services.participations import get_participation
from server.services.serialize import email_to_dict


def _now():
    return datetime.now(timezone.utc)


def get_email(session: Session, email_id) -> Email:
    e = session.get(Email, email_id)
    if e is None:
        raise NotFound(f"No email with id {email_id}.")
    return e


def list_emails(
    session: Session,
    status: str | None = None,
    campaign_id=None,
    has_unresolved_comments: bool | None = None,
    limit: int = 50,
) -> list[dict]:
    """Filterable read across all threads, with business context — e.g. every approved
    version, or every draft carrying unresolved operator feedback."""
    if status is not None and status not in EMAIL_STATUSES:
        raise ValidationRejected(f"status must be one of {', '.join(EMAIL_STATUSES)}.")
    unresolved = exists(
        select(Comment.id).where(
            Comment.entity_type == "email",
            Comment.entity_id == Email.id,
            Comment.resolved.is_(False),
        )
    )
    q = (
        select(Email, Participation, Business)
        .join(Participation, Email.participation_id == Participation.id)
        .join(Business, Participation.business_id == Business.id)
        .order_by(Email.created_at.desc())
        .limit(limit)
    )
    if status is not None:
        q = q.where(Email.status == status)
    if campaign_id is not None:
        q = q.where(Participation.campaign_id == campaign_id)
    if has_unresolved_comments is True:
        q = q.where(unresolved)
    elif has_unresolved_comments is False:
        q = q.where(~unresolved)
    rows = session.execute(q).all()
    counts = dict(
        session.execute(
            select(Comment.entity_id, func.count())
            .where(
                Comment.entity_type == "email",
                Comment.entity_id.in_([e.id for e, _, _ in rows]),
                Comment.resolved.is_(False),
            )
            .group_by(Comment.entity_id)
        ).all()
    ) if rows else {}
    return [
        {
            **email_to_dict(e),
            "business_id": str(b.id),
            "business_name": b.name,
            "category": p.category,
            "campaign_id": str(p.campaign_id),
            "participation_status": p.status,
            "unresolved_comments": counts.get(e.id, 0),
        }
        for e, p, b in rows
    ]


def save_draft(session: Session, participation_id, subject: str, body: str, author: str) -> dict:
    """New version in in_review; any prior in_review version is superseded.
    Operator edits come through here too — an edit is just the next version."""
    if author not in EMAIL_AUTHORS:
        raise ValidationRejected(f"author must be one of {', '.join(EMAIL_AUTHORS)}.")
    if not (subject or "").strip() or not (body or "").strip():
        raise ValidationRejected("A draft needs a non-empty subject and body.")
    p = get_participation(session, participation_id)
    if p.status == "declined":
        raise Conflict(
            "This participation was declined; drafting is closed. Re-attach the business to pitch again."
        )
    current = session.scalars(
        select(Email).where(Email.participation_id == p.id, Email.status == "in_review")
    ).first()
    if current is not None:
        current.status = "superseded"
    max_version = session.scalar(
        select(func.max(Email.version)).where(Email.participation_id == p.id)
    )
    e = Email(
        participation_id=p.id,
        version=(max_version or 0) + 1,
        author=author,
        subject=subject.strip(),
        body=body,
    )
    session.add(e)
    session.flush()
    return email_to_dict(e)


def approve(session: Session, email_id) -> dict:
    e = get_email(session, email_id)
    if e.status != "in_review":
        raise Conflict(
            f"Only an in_review version can be approved; version {e.version} is '{e.status}'. "
            "Approve the current in_review version instead."
        )
    e.status = "approved"
    e.approved_at = _now()
    session.flush()
    return email_to_dict(e)


def link_provider_draft(session: Session, email_id, provider: str, provider_draft_id: str) -> dict:
    """Record that the approved version now exists as a draft in the operator's own
    mailbox. One-way handoff, no sync-back: the approved version is canonical
    as-of-approval, and sending stays the operator's hand in their mail client."""
    if provider not in MAIL_PROVIDERS:
        raise ValidationRejected(f"provider must be one of {', '.join(MAIL_PROVIDERS)}.")
    draft_id = (provider_draft_id or "").strip()
    if not draft_id:
        raise ValidationRejected(
            "provider_draft_id is required — the draft id the mail provider returned."
        )
    e = get_email(session, email_id)
    if e.status == "in_review":
        raise Conflict(
            f"Version {e.version} is still in review. Only operator-approved versions go "
            "to the mailbox — never create external drafts for unapproved emails."
        )
    if e.status != "approved":
        raise Conflict(
            f"Version {e.version} is '{e.status}'; only the current approved version can "
            "be handed off."
        )
    if e.provider_draft_id:
        if e.provider_draft_id == draft_id and e.delivery_provider == provider:
            return email_to_dict(e)  # idempotent re-link
        raise Conflict(
            f"Version {e.version} is already linked to a {e.delivery_provider} draft "
            f"({e.provider_draft_id}). One approved email, one mailbox draft — if you "
            "created a duplicate, delete the one you just made and keep the linked draft."
        )
    e.delivery_provider = provider
    e.provider_draft_id = draft_id
    e.handed_off_at = _now()
    p = get_participation(session, e.participation_id)
    session.add(
        Interaction(
            business_id=p.business_id,
            participation_id=p.id,
            type="mail_draft_handed_off",
            payload={
                "email_id": str(e.id),
                "version": e.version,
                "provider": provider,
                "provider_draft_id": draft_id,
                "subject": e.subject,
            },
            occurred_at=_now(),
        )
    )
    session.flush()
    return email_to_dict(e)


def mark_sent(session: Session, email_id) -> dict:
    """Phase 1: the operator sent it from their own inbox and records the fact.
    Sent versions are immutable; the participation advances to contacted."""
    e = get_email(session, email_id)
    if e.status != "approved":
        raise Conflict(
            f"Only an approved version can be marked sent; version {e.version} is '{e.status}'. "
            "Approve it first — nothing is sendable without explicit approval."
        )
    e.status = "sent"
    e.sent_at = _now()
    p = get_participation(session, e.participation_id)
    if p.status == "prospecting":
        p.status = "contacted"
    session.add(
        Interaction(
            business_id=p.business_id,
            participation_id=p.id,
            type="email_sent",
            payload={"email_id": str(e.id), "version": e.version, "subject": e.subject},
            occurred_at=_now(),
        )
    )
    session.flush()
    return email_to_dict(e)
