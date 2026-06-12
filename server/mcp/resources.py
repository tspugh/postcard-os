"""MCP resources — stable knowledge that shouldn't consume tool calls. Single-sourced:
the markdown lives in server/guidance/ (also baked into plugin skills at build time);
sender and pricing are generated live from operator settings."""

from pathlib import Path

from fastmcp import FastMCP

from server.db import session_scope
from server.services.settings import get_settings

GUIDANCE_DIR = Path(__file__).resolve().parent.parent / "guidance"


def _guidance(name: str) -> str:
    return (GUIDANCE_DIR / name).read_text()


def register_resources(mcp: FastMCP) -> None:
    @mcp.resource("postcard://reference/workflow", mime_type="text/markdown")
    def workflow() -> str:
        """The state machines, the step-by-step playbook, and which tool effects which transition."""
        return _guidance("workflow.md")

    @mcp.resource("postcard://reference/research-strategy", mime_type="text/markdown")
    def research_strategy() -> str:
        """Discovery strategy: network out from researched/contacted leads into a web of leads; capture address and service area for proximity."""
        return _guidance("research-strategy.md")

    @mcp.resource("postcard://reference/quality-bars", mime_type="text/markdown")
    def quality_bars() -> str:
        """Staging bar, research bar, the disqualification vocabulary, and the active-is-protected guards."""
        return _guidance("quality-bars.md")

    @mcp.resource("postcard://reference/email-expectations", mime_type="text/markdown")
    def email_expectations() -> str:
        """What a good outreach email looks like — structure, tone, and the operator's instructions verbatim."""
        base = _guidance("email-expectations.md")
        with session_scope() as session:
            s = get_settings(session)
        instructions = s.outreach_instructions or "(none set yet — use the structural expectations above)"
        return (
            f"{base}\n\n## Operator's base tone\n\n{s.outreach_tone}\n"
            f"\n## Operator's outreach instructions (verbatim)\n\n{instructions}\n"
        )

    @mcp.resource("postcard://reference/sender", mime_type="text/markdown")
    def sender() -> str:
        """The operator's own business profile and personal notes — sender context for every email."""
        with session_scope() as session:
            s = get_settings(session)
        ob = s.operator_business or {}
        return (
            "# Sender profile (the operator's business)\n\n"
            f"- **Name:** {ob.get('name') or '(not set)'}\n"
            f"- **What we do:** {ob.get('description') or '(not set)'}\n"
            f"- **Personal notes for the agent:** {ob.get('personal_notes') or '(none)'}\n\n"
            f"## Email signature (use verbatim)\n\n{ob.get('signature') or '(not set)'}\n"
        )

    @mcp.resource("postcard://reference/slot-spec", mime_type="text/markdown")
    def slot_spec() -> str:
        """Slot JSON schema, constraints, exemplar and anti-example slots."""
        return _guidance("slot-spec.md")

    @mcp.resource("postcard://reference/template", mime_type="text/markdown")
    def template() -> str:
        """The active layout template(s): grid, dimensions, margins."""
        return _guidance("template.md")

    @mcp.resource("postcard://reference/pricing", mime_type="text/markdown")
    def pricing() -> str:
        """Pricing sheet generated from settings. Never invent a price."""
        with session_scope() as session:
            s = get_settings(session)
        dollars = s.default_slot_price_cents / 100
        return (
            "# Pricing sheet\n\n"
            f"- **Default slot price:** ${dollars:,.2f}/month ({s.default_slot_price_cents} cents)\n"
            f"- **Slots per card:** {s.default_total_slots}, one business per category\n"
            f"- **Market:** {s.seed_market}\n\n"
            "Attaching a business snapshots the campaign's price as its asking price; the\n"
            "negotiated number lands in committed_amount_cents at commitment. Settings\n"
            "changes never rewrite existing participations. Quote the asking price; never\n"
            "invent discounts.\n"
        )
