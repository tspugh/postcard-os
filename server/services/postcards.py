import re
from pathlib import Path

import nh3
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from server.errors import NotFound, ValidationRejected
from server.models import Business, Participation, PostcardDraft
from server.services.campaigns import get_campaign
from server.services.serialize import postcard_draft_to_dict

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(default=True, default_for_string=True),
)

ALLOWED_TAGS = {"b", "i", "em", "strong", "br", "span"}
ALLOWED_ATTRIBUTES = {"*": {"style"}}
ALLOWED_STYLE_PROPS = {"color", "font-size"}

SLOT_FIELDS = {"slot", "business_id", "headline", "offer_text", "contact_line", "logo_url", "accent_color", "offer_html"}
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{3,8}$")


def known_templates() -> list[str]:
    return sorted(p.name.removesuffix(".html.j2") for p in TEMPLATES_DIR.glob("*.html.j2"))


def _style_filter(tag: str, attribute: str, value: str):
    if attribute != "style":
        return value
    kept = []
    for decl in value.split(";"):
        if ":" not in decl:
            continue
        prop, _, val = decl.partition(":")
        if prop.strip().lower() in ALLOWED_STYLE_PROPS:
            kept.append(f"{prop.strip()}: {val.strip()}")
    return "; ".join(kept) or None


def sanitize_offer_html(fragment: str) -> str:
    """nh3 allowlist per TRD §5: b/i/em/strong/br/span, style limited to color/font-size."""
    return nh3.clean(
        fragment,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        attribute_filter=_style_filter,
        link_rel=None,
    )


def _validate_slots(session: Session, slots: list, total_slots: int) -> list[dict]:
    if not isinstance(slots, list) or not slots:
        raise ValidationRejected("slots must be a non-empty array of slot objects (see postcard://reference/slot-spec).")
    seen = set()
    problems = []
    for i, s in enumerate(slots):
        if not isinstance(s, dict):
            problems.append(f"slot[{i}] is not an object")
            continue
        unknown = set(s) - SLOT_FIELDS
        if unknown:
            problems.append(f"slot[{i}]: unknown fields {sorted(unknown)}; valid: {sorted(SLOT_FIELDS)}")
        n = s.get("slot")
        if not isinstance(n, int) or not (1 <= n <= total_slots):
            problems.append(f"slot[{i}]: 'slot' must be an integer 1..{total_slots}")
        elif n in seen:
            problems.append(f"slot[{i}]: slot number {n} appears twice")
        else:
            seen.add(n)
        headline = (s.get("headline") or "").strip()
        if not headline:
            problems.append(f"slot[{i}]: headline is required")
        elif len(headline.split()) > 6:
            problems.append(f"slot[{i}]: headline must be ≤ 6 words (got {len(headline.split())})")
        offer = (s.get("offer_text") or "").strip()
        if offer and len(offer.split()) > 12:
            problems.append(f"slot[{i}]: offer_text must be ≤ 12 words (got {len(offer.split())})")
        contact_line = s.get("contact_line") or ""
        if "\n" in contact_line:
            problems.append(f"slot[{i}]: contact_line must be a single line")
        accent = s.get("accent_color")
        if accent and not HEX_COLOR.match(accent):
            problems.append(f"slot[{i}]: accent_color must be a hex color like #1a6b3c")
        logo = s.get("logo_url")
        if logo and not re.match(r"^https?://", logo):
            problems.append(f"slot[{i}]: logo_url must be an http(s) URL")
        if s.get("business_id") and session.get(Business, s["business_id"]) is None:
            problems.append(f"slot[{i}]: business_id {s['business_id']} does not exist")
    if problems:
        raise ValidationRejected(
            "Postcard draft rejected — " + "; ".join(problems) + ". See postcard://reference/slot-spec."
        )
    return slots


def save_draft(
    session: Session,
    campaign_id,
    slots: list,
    template_id: str | None = None,
    notes: str | None = None,
) -> dict:
    campaign = get_campaign(session, campaign_id)
    template_id = template_id or "grid-4x2-v1"
    if template_id not in known_templates():
        raise ValidationRejected(
            f"Unknown template_id '{template_id}'. Available templates: {', '.join(known_templates())}. "
            "The agent never writes template HTML — slot content only."
        )
    slots = _validate_slots(session, slots, campaign.total_slots)
    max_version = session.scalar(
        select(func.max(PostcardDraft.version)).where(PostcardDraft.campaign_id == campaign.id)
    )
    d = PostcardDraft(
        campaign_id=campaign.id,
        version=(max_version or 0) + 1,
        template_id=template_id,
        slots=slots,
        notes=notes,
    )
    session.add(d)
    session.flush()
    return postcard_draft_to_dict(d)


def list_drafts(session: Session, campaign_id) -> list[dict]:
    get_campaign(session, campaign_id)
    rows = session.scalars(
        select(PostcardDraft).where(PostcardDraft.campaign_id == campaign_id).order_by(PostcardDraft.version.desc())
    )
    return [postcard_draft_to_dict(d) for d in rows]


def render(session: Session, campaign_id, version: int | None = None) -> dict:
    """Slots JSON → Jinja template → sanitized HTML. Empty slots render as labeled
    placeholders so the operator sees the card as it would print today."""
    campaign = get_campaign(session, campaign_id)
    q = select(PostcardDraft).where(PostcardDraft.campaign_id == campaign.id)
    if version is not None:
        draft = session.scalars(q.where(PostcardDraft.version == version)).first()
        if draft is None:
            raise NotFound(f"No postcard draft version {version} for '{campaign.name}'.")
    else:
        draft = session.scalars(q.order_by(PostcardDraft.version.desc())).first()
        if draft is None:
            raise NotFound(f"No postcard drafts yet for '{campaign.name}'. Save one first.")

    by_number = {s["slot"]: dict(s) for s in draft.slots}
    slot_categories = {
        p.slot_number: p.category
        for p in session.scalars(
            select(Participation).where(
                Participation.campaign_id == campaign.id,
                Participation.slot_number.is_not(None),
            )
        )
    }
    cells = []
    for n in range(1, campaign.total_slots + 1):
        s = by_number.get(n)
        if s is None:
            cells.append({"slot": n, "empty": True, "category_label": slot_categories.get(n, "open slot")})
        else:
            if s.get("offer_html"):
                s["offer_html"] = sanitize_offer_html(s["offer_html"])
            s["empty"] = False
            cells.append(s)

    template = _env.get_template(f"{draft.template_id}.html.j2")
    html = template.render(
        campaign=campaign,
        header=f"{campaign.market.split(',')[0]} Local Business Spotlight — {campaign.month.strftime('%B')}",
        cells=cells,
    )
    return {
        "campaign_id": str(campaign.id),
        "version": draft.version,
        "template_id": draft.template_id,
        "html": html,
        "iframe_sandbox": "",  # render inside <iframe sandbox=""> — scripts and navigation disabled
    }
