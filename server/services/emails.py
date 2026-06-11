from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from server.errors import Conflict, NotFound, ValidationRejected
from server.models import EMAIL_AUTHORS, Email, Interaction
from server.services.participations import get_participation
from server.services.serialize import email_to_dict


def _now():
    return datetime.now(timezone.utc)


def get_email(session: Session, email_id) -> Email:
    e = session.get(Email, email_id)
    if e is None:
        raise NotFound(f"No email with id {email_id}.")
    return e


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
