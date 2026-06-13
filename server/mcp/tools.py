"""MCP tools — each is a transition in the lead state machine, a thin wrapper over one
service function. The tool surface IS the workflow; operator-only actions (approve,
mark-sent, promote, reorder, payment, fulfillment, archive) are deliberately absent."""

import uuid
from datetime import date
from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from server.db import session_scope
from server.errors import DomainError
from server.services import (
    businesses as business_service,
    campaigns as campaign_service,
    comments as comment_service,
    contacts as contact_service,
    emails as email_service,
    participations as participation_service,
    postcards as postcard_service,
    summary as summary_service,
)

READ_ONLY = {"readOnlyHint": True}
NON_DESTRUCTIVE = {"destructiveHint": False, "readOnlyHint": False}
GUARDED_DESTRUCTIVE = {"destructiveHint": True, "readOnlyHint": False}


def _uuid(value: str, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        raise ToolError(f"'{value}' is not a valid {what} id (expected a UUID).")


def _date(value: str, what: str, allow_month_only: bool = False) -> date:
    raw = (value or "").strip()
    if allow_month_only and len(raw) == 7:
        raw += "-01"
    try:
        return date.fromisoformat(raw)
    except ValueError:
        expected = "YYYY-MM or YYYY-MM-DD" if allow_month_only else "YYYY-MM-DD"
        raise ToolError(f"'{value}' is not a valid {what} (expected {expected}).")


NO_CAMPAIGN_HINT = (
    " Note: there is no active campaign right now, so there is nothing to attach businesses "
    "to or draft against. Tell the operator to create a campaign in the dashboard so you can "
    "proceed — or, ONLY if the operator has explicitly asked you for a new campaign, create "
    "it with postcard_create_campaign."
)


def _hint_if_no_campaign(session, message: str) -> str:
    """Campaign-dependent tools fail confusingly when the real problem is that no
    campaign exists yet — append the way forward."""
    if campaign_service.active_campaign(session) is None:
        return message + NO_CAMPAIGN_HINT
    return message


class LeadIn(BaseModel):
    name: str | None = Field(None, description="Business name (staging bar: required)")
    category: str | None = Field(None, description="Category tag from settings vocabulary (staging bar: required)")
    website: str | None = Field(None, description="Working website URL — proof of existence (staging bar: required)")
    note: str | None = Field(None, description="Optional free-form note about the find")


class ContactIn(BaseModel):
    name: str | None = None
    title: str | None = Field(None, description="e.g. 'owner', 'office manager'")
    email: str | None = None
    email_source: str | None = Field(None, description="URL or page where the email was found (required with email)")
    email_confidence: str | None = Field(None, description="'listed' | 'scraped' | 'guessed' (required with email)")
    phone: str | None = None
    is_primary: bool = False


class ResearchIn(BaseModel):
    premise: str | None = Field(None, description="2-3 factual sentences: what the business does and for whom")
    hooks: list[str] = Field(default_factory=list, description="Specific personalization ammunition, ≥1")
    evidence_urls: list[str] = Field(default_factory=list, description="URLs backing the claims, ≥1")
    contacts: list[ContactIn] = Field(default_factory=list, description="≥1 contact with email or phone")


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool(annotations=READ_ONLY)
    def postcard_get_campaign_status(campaign_id: str | None = None) -> dict:
        """Orient yourself — ALWAYS the first call of a session. Returns the campaign (active
        one by default), slot/category fill map, every waitlist in order, pipeline counts, and
        the operator's settings inline: default price, category vocabulary, seed market,
        sender business profile, and outreach instructions. The campaign board also carries
        your two worklists: approved_awaiting_handoff — operator-approved emails not yet
        placed into their mailbox as drafts (see postcard://reference/mail-handoff) — and
        revision_requests — drafts with unresolved operator feedback newer than your latest
        version (read the comments, save the next version)."""
        with session_scope() as session:
            try:
                return summary_service.get_campaign_status(
                    session, _uuid(campaign_id, "campaign") if campaign_id else None
                )
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_create_campaign(
        month: str,
        deadline: str,
        name: str | None = None,
        market: str | None = None,
    ) -> dict:
        """Create a campaign (one postcard run). OPERATOR-GATED: call this only when the
        operator has explicitly asked for a new campaign — never to unblock yourself, and
        never speculatively. Campaigns are archived, not deleted, so a stray one lingers
        forever. month is 'YYYY-MM' (or 'YYYY-MM-DD'); deadline is 'YYYY-MM-DD'. name
        defaults to 'market + month'; market defaults to the seed market in settings.
        Multiple campaigns may run in the same month — when more than one is active, pass
        campaign_id explicitly to the other tools."""
        with session_scope() as session:
            try:
                return campaign_service.create_campaign(
                    session,
                    month=_date(month, "month", allow_month_only=True),
                    deadline=_date(deadline, "deadline"),
                    name=name,
                    market=market,
                )
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=READ_ONLY)
    def postcard_list_staged_leads(limit: int = 50) -> list[dict]:
        """Staged businesses awaiting research, oldest first. Claim one with
        postcard_claim_lead before researching it."""
        with session_scope() as session:
            return business_service.list_staged(session, limit=limit)

    @mcp.tool(annotations=READ_ONLY)
    def postcard_list_businesses(
        status: str | None = None, category: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Read the pipeline: businesses with their research record (website, premise, hooks,
        evidence URLs, address, service_area) and contacts, newest first. Filter by status
        (staged/researching/researched/disqualified) and/or category. Use researched and
        contacted businesses as seeds to network out to new leads — see
        postcard://reference/research-strategy."""
        with session_scope() as session:
            if status is not None and status not in ("staged", "researching", "researched", "disqualified"):
                raise ToolError(
                    f"'{status}' is not a business status. Valid: staged, researching, "
                    "researched, disqualified."
                )
            return business_service.list_businesses(session, status=status, category=category, limit=limit)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_stage_leads(leads: list[LeadIn]) -> dict:
        """Bulk-stage leads found through discovery. Staging bar (enforced): name + category +
        working website URL. Duplicates are rejected naming the existing record. Returns
        {staged, rejected} — rejections explain exactly what was missing."""
        with session_scope() as session:
            try:
                return business_service.stage_leads(session, [l.model_dump() for l in leads])
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_claim_lead(business_id: str) -> dict:
        """Claim a staged lead exclusively before researching (staged → researching). Claims
        older than 1 hour are reclaimable."""
        with session_scope() as session:
            try:
                return business_service.claim_lead(session, _uuid(business_id, "business"))
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_submit_research(business_id: str, research: ResearchIn) -> dict:
        """Submit structured research (researching → researched). Research bar (enforced):
        ≥1 contact with email or phone (email needs source + confidence), a premise, ≥1 hook,
        ≥1 evidence URL. Contacts become rows you can correct later with postcard_save_contact."""
        with session_scope() as session:
            try:
                return business_service.submit_research(
                    session, _uuid(business_id, "business"), research.model_dump()
                )
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_update_business(business_id: str, fields: dict[str, Any]) -> dict:
        """Partial update of business details as you learn more: address, service_area,
        premise, hooks, evidence_urls, category. Contacts have their own tools."""
        with session_scope() as session:
            try:
                return business_service.update_business(session, _uuid(business_id, "business"), fields)
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_save_contact(business_id: str, contact: ContactIn, contact_id: str | None = None) -> dict:
        """Add a contact (omit contact_id) or correct one (pass contact_id). A contact needs
        an email or phone; an email needs source + confidence (listed/scraped/guessed)."""
        with session_scope() as session:
            try:
                return contact_service.save_contact(
                    session,
                    _uuid(business_id, "business"),
                    {k: v for k, v in contact.model_dump().items() if v is not None},
                    contact_id=_uuid(contact_id, "contact") if contact_id else None,
                )
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=GUARDED_DESTRUCTIVE)
    def postcard_delete_contact(contact_id: str) -> dict:
        """Remove a contact. Guarded: the last reachable contact on an active advertiser
        cannot be deleted — correct it with postcard_save_contact instead."""
        with session_scope() as session:
            try:
                return contact_service.delete_contact(session, _uuid(contact_id, "contact"))
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_disqualify_lead(business_id: str, dq_code: str, reason: str | None = None) -> dict:
        """Take a dead-end lead out of the pipeline, auditable. dq_code from the closed
        vocabulary: no_contact_info, defunct, bad_fit, duplicate, do_not_contact, other
        ('other' requires a reason). Guarded: active advertisers cannot be disqualified."""
        with session_scope() as session:
            try:
                return business_service.disqualify(session, _uuid(business_id, "business"), dq_code, reason)
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_add_to_campaign(campaign_id: str, business_id: str, category: str | None = None) -> dict:
        """Attach a researched business to a campaign, creating a participation in
        'prospecting'. Snapshots the campaign's slot price as the asking price. Category
        defaults to the business's tag."""
        with session_scope() as session:
            try:
                return participation_service.add_to_campaign(
                    session, _uuid(campaign_id, "campaign"), _uuid(business_id, "business"), category
                )
            except DomainError as e:
                raise ToolError(_hint_if_no_campaign(session, e.message))

    @mcp.tool(annotations=GUARDED_DESTRUCTIVE)
    def postcard_remove_from_campaign(participation_id: str) -> dict:
        """Detach a participation. Allowed only in prospecting/contacted — past that the
        relationship is history and the operator declines it instead."""
        with session_scope() as session:
            try:
                return participation_service.remove_from_campaign(session, _uuid(participation_id, "participation"))
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_save_email_draft(participation_id: str, subject: str, body: str) -> dict:
        """Save an outreach draft. Every save is a new version placed in_review — nothing you
        write is sendable without operator approval. Prior in-review versions are superseded.
        Read postcard://reference/email-expectations before drafting."""
        with session_scope() as session:
            try:
                return email_service.save_draft(
                    session, _uuid(participation_id, "participation"), subject, body, author="agent"
                )
            except DomainError as e:
                raise ToolError(_hint_if_no_campaign(session, e.message))

    @mcp.tool(annotations=READ_ONLY)
    def postcard_list_emails(
        status: str | None = None,
        campaign_id: str | None = None,
        has_unresolved_comments: bool | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Read email versions across all threads with business context, newest first.
        Filter by status (in_review/approved/sent/superseded), campaign, and/or unresolved
        operator feedback — e.g. status='approved' for every approved version (including
        already-handed-off ones), or has_unresolved_comments=true for drafts awaiting your
        revision. Each row carries unresolved_comments and the mail-handoff fields."""
        with session_scope() as session:
            try:
                return email_service.list_emails(
                    session,
                    status=status,
                    campaign_id=_uuid(campaign_id, "campaign") if campaign_id else None,
                    has_unresolved_comments=has_unresolved_comments,
                    limit=limit,
                )
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_link_mail_draft(email_id: str, provider_draft_id: str, provider: str = "gmail") -> dict:
        """After you place an APPROVED email into the operator's mailbox as a draft (via
        their connected mail tool — Gmail first), record the linkage here so the dashboard
        shows it. Subject and body go to the mailbox verbatim, addressed to the contact on
        record; only approved versions can be handed off, and you never send. Read
        postcard://reference/mail-handoff before your first handoff."""
        with session_scope() as session:
            try:
                return email_service.link_provider_draft(
                    session, _uuid(email_id, "email"), provider, provider_draft_id
                )
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=READ_ONLY)
    def postcard_get_comments(entity_type: str, entity_id: str, unresolved_only: bool = False) -> list[dict]:
        """Operator feedback on an email ('email', email id), a postcard slot
        ('postcard_slot', draft id — slot_number on each comment), or a business. Respond to
        comments by saving the next version, not by replying."""
        with session_scope() as session:
            try:
                return comment_service.list_comments(
                    session, entity_type, _uuid(entity_id, "entity"), unresolved_only=unresolved_only
                )
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_record_commitment(participation_id: str, amount_cents: int) -> dict:
        """Record a relayed 'yes' with the negotiated amount in cents (may differ from asking
        price). Checks category exclusivity and assigns a slot. If the category is already
        won, the rejection will tell you to use postcard_move_to_waitlist — do that."""
        with session_scope() as session:
            try:
                return participation_service.record_commitment(
                    session, _uuid(participation_id, "participation"), amount_cents
                )
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_move_to_waitlist(participation_id: str) -> dict:
        """Move an interested advertiser to their category's waitlist (appended in order).
        Use this when exclusivity blocks a commitment — waitlists are preserved revenue and
        carry forward to the next campaign. Promotion is the operator's call."""
        with session_scope() as session:
            try:
                return participation_service.move_to_waitlist(session, _uuid(participation_id, "participation"))
            except DomainError as e:
                raise ToolError(e.message)

    @mcp.tool(annotations=NON_DESTRUCTIVE)
    def postcard_save_postcard_draft(
        campaign_id: str,
        slots: list[dict[str, Any]],
        template_id: str | None = None,
        notes: str | None = None,
    ) -> dict:
        """Save a postcard draft: structured slot JSON inside a versioned, frozen template
        (default grid-4x2-v1). You cannot break the layout — constraints are enforced per
        slot. See postcard://reference/slot-spec for the schema and exemplars."""
        with session_scope() as session:
            try:
                return postcard_service.save_draft(
                    session, _uuid(campaign_id, "campaign"), slots, template_id=template_id, notes=notes
                )
            except DomainError as e:
                raise ToolError(_hint_if_no_campaign(session, e.message))
