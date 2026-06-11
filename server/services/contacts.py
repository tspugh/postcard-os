from sqlalchemy import select
from sqlalchemy.orm import Session

from server.errors import Conflict, NotFound, ValidationRejected
from server.models import ACTIVE_PARTICIPATION_STATUSES, Business, Contact, EMAIL_CONFIDENCES, Participation
from server.services.serialize import contact_to_dict

CONTACT_FIELDS = {"name", "title", "email", "email_source", "email_confidence", "phone", "is_primary"}


def validate_contact_payload(payload: dict, partial_base: Contact | None = None) -> str | None:
    """Returns an actionable problem string, or None if the (merged) contact is valid."""
    unknown = set(payload) - CONTACT_FIELDS
    if unknown:
        return f"unknown fields {sorted(unknown)}; valid fields: {sorted(CONTACT_FIELDS)}"

    def merged(field):
        if field in payload:
            return payload[field]
        return getattr(partial_base, field) if partial_base is not None else None

    email, phone = merged("email"), merged("phone")
    if not (email or phone):
        return "a contact must have an email or a phone (it is not reachable otherwise)"
    if email:
        if not merged("email_source"):
            return "an email needs email_source (the URL or page where it was found)"
        confidence = merged("email_confidence")
        if confidence not in EMAIL_CONFIDENCES:
            return f"email_confidence must be one of {', '.join(EMAIL_CONFIDENCES)}"
    return None


def _get_contact(session: Session, contact_id) -> Contact:
    c = session.get(Contact, contact_id)
    if c is None:
        raise NotFound(f"No contact with id {contact_id}.")
    return c


def save_contact(session: Session, business_id, contact: dict, contact_id=None) -> dict:
    b = session.get(Business, business_id)
    if b is None:
        raise NotFound(f"No business with id {business_id}.")
    if b.status == "disqualified":
        raise Conflict(f"'{b.name}' is disqualified; disqualified records are read-only.")

    existing = _get_contact(session, contact_id) if contact_id else None
    if existing is not None and existing.business_id != b.id:
        raise ValidationRejected(f"Contact {contact_id} belongs to a different business.")

    err = validate_contact_payload(contact, partial_base=existing)
    if err:
        raise ValidationRejected(f"Contact rejected — {err}.")

    if contact.get("is_primary"):
        for other in session.scalars(
            select(Contact).where(Contact.business_id == b.id, Contact.is_primary)
        ):
            if existing is None or other.id != existing.id:
                other.is_primary = False
        session.flush()

    if existing is None:
        has_primary = session.scalars(
            select(Contact).where(Contact.business_id == b.id, Contact.is_primary)
        ).first()
        row = Contact(
            business_id=b.id,
            **{f: contact.get(f) for f in CONTACT_FIELDS - {"is_primary"}},
            is_primary=bool(contact.get("is_primary")) or has_primary is None,
        )
        session.add(row)
    else:
        row = existing
        for field in CONTACT_FIELDS & set(contact):
            setattr(row, field, contact[field])
    session.flush()
    return contact_to_dict(row)


def delete_contact(session: Session, contact_id) -> dict:
    c = _get_contact(session, contact_id)
    b = session.get(Business, c.business_id)
    has_active = session.scalars(
        select(Participation).where(
            Participation.business_id == b.id,
            Participation.status.in_(ACTIVE_PARTICIPATION_STATUSES),
        )
    ).first()
    if has_active is not None:
        reachable_others = [
            o for o in session.scalars(select(Contact).where(Contact.business_id == b.id, Contact.id != c.id))
            if o.email or o.phone
        ]
        if not reachable_others:
            raise Conflict(
                f"Cannot delete the last reachable contact on '{b.name}' — it is an active advertiser "
                f"(participation status '{has_active.status}'). Corrections go through edits: "
                "use postcard_save_contact with contact_id to fix the record instead."
            )
    was_primary = c.is_primary
    session.delete(c)
    session.flush()
    if was_primary:
        successor = session.scalars(
            select(Contact).where(Contact.business_id == b.id).order_by(Contact.created_at)
        ).first()
        if successor is not None:
            successor.is_primary = True
            session.flush()
    return {"deleted": str(contact_id), "business_id": str(b.id)}
