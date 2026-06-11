from sqlalchemy import select
from sqlalchemy.orm import Session

from server.errors import ValidationRejected
from server.models import CANONICAL_CATEGORIES, Settings

EDITABLE_FIELDS = {
    "default_slot_price_cents",
    "default_total_slots",
    "categories",
    "seed_market",
    "operator_business",
    "outreach_instructions",
}


def get_settings(session: Session) -> Settings:
    """Fetch the single settings row, creating it with seeded defaults on first run."""
    row = session.scalars(select(Settings)).first()
    if row is None:
        row = Settings(categories=list(CANONICAL_CATEGORIES))
        session.add(row)
        session.flush()
    return row


def update_settings(session: Session, fields: dict) -> Settings:
    unknown = set(fields) - EDITABLE_FIELDS
    if unknown:
        raise ValidationRejected(
            f"Unknown settings fields: {sorted(unknown)}. Editable fields: {sorted(EDITABLE_FIELDS)}."
        )
    if "categories" in fields:
        cats = fields["categories"]
        if not isinstance(cats, list) or not cats or not all(isinstance(c, str) and c.strip() for c in cats):
            raise ValidationRejected("categories must be a non-empty list of non-empty strings.")
        fields["categories"] = [c.strip().lower() for c in cats]
    for key in ("default_slot_price_cents", "default_total_slots"):
        if key in fields and (not isinstance(fields[key], int) or fields[key] <= 0):
            raise ValidationRejected(f"{key} must be a positive integer.")
    row = get_settings(session)
    for key, value in fields.items():
        setattr(row, key, value)
    session.flush()
    return row


def settings_to_dict(s: Settings) -> dict:
    return {
        "default_slot_price_cents": s.default_slot_price_cents,
        "default_total_slots": s.default_total_slots,
        "categories": s.categories,
        "seed_market": s.seed_market,
        "operator_business": s.operator_business,
        "outreach_instructions": s.outreach_instructions,
    }
