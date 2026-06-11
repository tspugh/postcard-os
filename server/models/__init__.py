import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Vocabularies (mirrored as Postgres enums; service rules reference these)
ENRICHMENT_STATUSES = ("staged", "researching", "researched", "disqualified")
DQ_REASON_CODES = ("no_contact_info", "defunct", "bad_fit", "duplicate", "do_not_contact", "other")
CAMPAIGN_STATUSES = ("draft", "filling", "full", "fulfillment", "completed", "archived")
OUTREACH_STATUSES = ("prospecting", "contacted", "interested", "waitlisted", "committed", "paid", "declined")
EMAIL_STATUSES = ("in_review", "approved", "sent", "superseded")
EMAIL_AUTHORS = ("agent", "operator")
COMMENT_ENTITIES = ("email", "postcard_slot", "business")
EMAIL_CONFIDENCES = ("listed", "scraped", "guessed")

# "Active is protected": prospecting through paid (everything except declined).
ACTIVE_PARTICIPATION_STATUSES = ("prospecting", "contacted", "interested", "waitlisted", "committed", "paid")

CANONICAL_CATEGORIES = ["roofer", "plumber", "electrician", "hvac", "landscaper", "auto repair", "realtor", "restaurant"]

FULFILLMENT_KEYS = ("logo_received", "offer_confirmed", "artwork_approved", "logo_url")
FULFILLMENT_CHECKLIST_KEYS = ("logo_received", "offer_confirmed", "artwork_approved")

DEFAULT_TEMPLATE_ID = "grid-4x2-v1"


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Settings(TimestampMixin, Base):
    """Single-row control panel; the boolean PK + CHECK enforce exactly one row."""

    __tablename__ = "settings"
    __table_args__ = (CheckConstraint("id", name="settings_single_row"),)

    id: Mapped[bool] = mapped_column(Boolean, primary_key=True, default=True, server_default=text("true"))
    default_slot_price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=29900, server_default=text("29900"))
    default_total_slots: Mapped[int] = mapped_column(Integer, nullable=False, default=8, server_default=text("8"))
    categories: Mapped[list] = mapped_column(JSONB, nullable=False, default=lambda: list(CANONICAL_CATEGORIES))
    seed_market: Mapped[str] = mapped_column(Text, nullable=False, default="Lafayette, IN", server_default=text("'Lafayette, IN'"))
    operator_business: Mapped[dict | None] = mapped_column(JSONB)  # {name, description, personal_notes, signature}
    outreach_instructions: Mapped[str | None] = mapped_column(Text)


class Business(TimestampMixin, Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)  # tag from settings vocabulary (advisory, not FK)
    website: Mapped[str] = mapped_column(Text, nullable=False)  # STAGING BAR: proof of real business
    address: Mapped[str | None] = mapped_column(Text)
    service_area: Mapped[str | None] = mapped_column(Text)
    premise: Mapped[str | None] = mapped_column(Text)  # factual orientation, one per business
    hooks: Mapped[list | None] = mapped_column(JSONB)  # personalization ammunition
    evidence_urls: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        Enum(*ENRICHMENT_STATUSES, name="enrichment_status"), nullable=False, default="staged", server_default=text("'staged'")
    )
    dq_code: Mapped[str | None] = mapped_column(Enum(*DQ_REASON_CODES, name="dq_reason_code"))
    dq_reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)  # 'agent:web' | 'operator' | ...
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    operator_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    contacts: Mapped[list["Contact"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    participations: Mapped[list["Participation"]] = relationship(back_populates="business")


class Contact(TimestampMixin, Base):
    __tablename__ = "contacts"
    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="contact_reachable"),
        Index("one_primary_contact", "business_id", unique=True, postgresql_where=text("is_primary")),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    email_source: Mapped[str | None] = mapped_column(Text)
    email_confidence: Mapped[str | None] = mapped_column(Text)  # 'listed' | 'scraped' | 'guessed'
    phone: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    business: Mapped[Business] = relationship(back_populates="contacts")


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    market: Mapped[str] = mapped_column(Text, nullable=False)
    month: Mapped[Date] = mapped_column(Date, nullable=False)
    deadline: Mapped[Date] = mapped_column(Date, nullable=False)
    slot_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)  # snapshot of settings default
    total_slots: Mapped[int] = mapped_column(Integer, nullable=False)  # snapshot of settings default
    status: Mapped[str] = mapped_column(
        Enum(*CAMPAIGN_STATUSES, name="campaign_status"), nullable=False, default="draft", server_default=text("'draft'")
    )

    participations: Mapped[list["Participation"]] = relationship(back_populates="campaign")


class Participation(TimestampMixin, Base):
    __tablename__ = "participations"
    __table_args__ = (
        UniqueConstraint("campaign_id", "business_id", name="one_participation_per_business"),
        Index(
            "one_committed_per_category",
            "campaign_id",
            "category",
            unique=True,
            postgresql_where=text("status IN ('committed','paid')"),
        ),
        Index(
            "waitlist_position",
            "campaign_id",
            "category",
            "waitlist_order",
            unique=True,
            postgresql_where=text("status = 'waitlisted'"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)  # copied from business at attach; editable
    status: Mapped[str] = mapped_column(
        Enum(*OUTREACH_STATUSES, name="outreach_status"), nullable=False, default="prospecting", server_default=text("'prospecting'")
    )
    asking_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)  # snapshot at attach
    committed_amount_cents: Mapped[int | None] = mapped_column(Integer)
    payment_status: Mapped[str | None] = mapped_column(Text)  # 'pending' | 'paid'
    payment_method: Mapped[str | None] = mapped_column(Text)  # 'cash' | 'paypal' | 'check' | 'other'
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    waitlist_order: Mapped[int | None] = mapped_column(Integer)
    fulfillment: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    slot_number: Mapped[int | None] = mapped_column(Integer)

    campaign: Mapped[Campaign] = relationship(back_populates="participations")
    business: Mapped[Business] = relationship(back_populates="participations")
    emails: Mapped[list["Email"]] = relationship(back_populates="participation")


class Email(TimestampMixin, Base):
    __tablename__ = "emails"
    __table_args__ = (UniqueConstraint("participation_id", "version", name="one_version_per_participation"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    participation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participations.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    author: Mapped[str] = mapped_column(Enum(*EMAIL_AUTHORS, name="email_author"), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(*EMAIL_STATUSES, name="email_status"), nullable=False, default="in_review", server_default=text("'in_review'")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    participation: Mapped[Participation] = relationship(back_populates="emails")


class Comment(TimestampMixin, Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = uuid_pk()
    entity_type: Mapped[str] = mapped_column(Enum(*COMMENT_ENTITIES, name="comment_entity"), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    slot_number: Mapped[int | None] = mapped_column(Integer)  # only for postcard_slot
    author: Mapped[str] = mapped_column(Text, nullable=False)  # 'grant' | 'agent'
    body: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))


class Interaction(TimestampMixin, Base):
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    participation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("participations.id"))
    type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AgentActivity(Base):
    __tablename__ = "agent_activity"

    id: Mapped[uuid.UUID] = uuid_pk()
    tool_name: Mapped[str] = mapped_column(Text, nullable=False)
    args_summary: Mapped[dict | None] = mapped_column(JSONB)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)  # 'ok' | 'rejected' | 'error'
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PostcardDraft(TimestampMixin, Base):
    __tablename__ = "postcard_drafts"
    __table_args__ = (UniqueConstraint("campaign_id", "version", name="one_postcard_version_per_campaign"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template_id: Mapped[str] = mapped_column(Text, nullable=False, default=DEFAULT_TEMPLATE_ID, server_default=text("'grid-4x2-v1'"))
    slots: Mapped[list] = mapped_column(JSONB, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
