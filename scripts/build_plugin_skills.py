"""Generate plugin skills from server/guidance — the single source (TRD §1).
Run via `make build-skills` whenever guidance changes; commit the output."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDANCE = ROOT / "server" / "guidance"
SKILLS = ROOT / "plugin" / "skills"

GENERATED_NOTE = (
    "<!-- GENERATED from server/guidance/ by scripts/build_plugin_skills.py — edit there, "
    "then `make build-skills`. -->"
)

RESEARCH_FRONTMATTER = """---
name: lead-research
description: Discover and research local business leads through the postcard MCP — stage candidates, claim and research them to the quality bar, and network out from already-contacted leads into a web of researched prospects. Use when finding or researching businesses for the postcard pipeline.
---
"""

RESEARCH_FRAMING = """
# Lead research — session ritual

1. **Orient first, always:** call `postcard_get_campaign_status`. It carries the settings
   (price, categories, market), the fill map, and pipeline counts. The seed market and the
   category vocabulary scope everything you discover.
2. **Network out before searching cold:** read the existing web with
   `postcard_list_businesses` (researched, plus the campaign board's contacted/interested
   participations) and follow its edges — neighbors, named partners, shared directories —
   per the discovery strategy below.
3. Stage what clears the staging bar, claim before researching, research to the research bar,
   and record each business's address and service area as you go.
4. Hard rules: never research a disqualified lead; never re-stage a rejected duplicate —
   work the existing record; disqualify dead ends with a reason code, never silently drop them.
"""

OUTREACH_FRONTMATTER = """---
name: campaign-outreach
description: Compose a postcard campaign from researched businesses and draft outreach emails for human review — attach leads, draft and revise versioned emails, record commitments, and use waitlists when categories fill. Use when working a campaign or writing outreach.
---
"""

OUTREACH_FRAMING = """
# Campaign outreach — session ritual

1. **Orient first, always:** call `postcard_get_campaign_status`. It carries the settings
   (price, categories, market), the sender profile, the outreach instructions, the fill map,
   and every waitlist. Do not attach or draft before orienting.
2. **Compose from what is researched:** `postcard_list_businesses` with `status="researched"`
   is the pool of pitch-ready leads. Fill empty categories first; prior-campaign waitlisted
   businesses are priority prospects. Attach with `postcard_add_to_campaign`, then draft an
   email for every attached business — a participation without a draft is dead inventory.
3. Work the pipeline with the playbook below. The bars are enforced by the tools; when a tool
   rejects you, the error tells you the valid next action — follow it.
4. Hard rules: never imply an email was sent (the operator sends from their own inbox);
   when exclusivity blocks a commitment, move the advertiser to the waitlist; never invent
   a price; campaign creation is the operator's explicit call, never yours to unblock yourself.
"""

POSTCARD_FRONTMATTER = """---
name: postcard-design
description: Design postcard slot content — structured JSON inside a frozen versioned template, with legibility rules and slot-anchored feedback. Use when drafting or revising the postcard for a campaign.
---
"""

POSTCARD_FRAMING = """
# Postcard design

You design slot *content*, never layout: structured JSON per slot inside a frozen template
(`postcard_save_postcard_draft`). Read slot-anchored operator feedback with
`postcard_get_comments` (`entity_type="postcard_slot"`, the draft id) and respond by saving
the next draft version.

Legibility rules: contrast ≥ 4.5:1, one focal element per slot, ≤ 2 type sizes per slot.
Empty slots stay visible as labeled placeholders — the operator sees the card as it would
print today.
"""

SKILL_SPECS = {
    "lead-research": [
        RESEARCH_FRONTMATTER,
        RESEARCH_FRAMING,
        "research-strategy.md",
        "workflow.md",
        "quality-bars.md",
    ],
    "campaign-outreach": [
        OUTREACH_FRONTMATTER,
        OUTREACH_FRAMING,
        "workflow.md",
        "email-expectations.md",
    ],
    "postcard-design": [
        POSTCARD_FRONTMATTER,
        POSTCARD_FRAMING,
        "slot-spec.md",
        "template.md",
    ],
}


def read(name: str) -> str:
    return (GUIDANCE / name).read_text().strip()


def build():
    for skill, parts in SKILL_SPECS.items():
        frontmatter, framing, *sources = parts
        body = "\n\n".join(
            [frontmatter.strip(), GENERATED_NOTE, framing.strip(), *(read(s) for s in sources)]
        )
        (SKILLS / skill).mkdir(parents=True, exist_ok=True)
        (SKILLS / skill / "SKILL.md").write_text(body + "\n")
        print(f"wrote plugin/skills/{skill}/SKILL.md")


if __name__ == "__main__":
    build()
