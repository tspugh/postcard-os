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

OUTREACH_FRONTMATTER = """---
name: outreach
description: Work the postcard lead pipeline — stage, claim, research local businesses, draft outreach emails for human review, record commitments, and use waitlists when categories fill. Use whenever operating the postcard MCP server.
---
"""

OUTREACH_FRAMING = """
# Outreach — session ritual

1. **Orient first, always:** call `postcard_get_campaign_status`. It carries the settings
   (price, categories, market), the sender profile, the outreach instructions, the fill map,
   and every waitlist. Do not stage, research, or draft before orienting.
2. Work the pipeline with the playbook below. The bars are enforced by the tools; when a tool
   rejects you, the error tells you the valid next action — follow it.
3. Hard rules: never imply an email was sent (the operator sends from their own inbox);
   never research a disqualified lead; when exclusivity blocks a commitment, move the
   advertiser to the waitlist; never invent a price.
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


def read(name: str) -> str:
    return (GUIDANCE / name).read_text().strip()


def build():
    outreach = "\n\n".join(
        [
            OUTREACH_FRONTMATTER.strip(),
            GENERATED_NOTE,
            OUTREACH_FRAMING.strip(),
            read("workflow.md"),
            read("quality-bars.md"),
            read("email-expectations.md"),
        ]
    )
    postcard = "\n\n".join(
        [
            POSTCARD_FRONTMATTER.strip(),
            GENERATED_NOTE,
            POSTCARD_FRAMING.strip(),
            read("slot-spec.md"),
            read("template.md"),
        ]
    )
    (SKILLS / "outreach").mkdir(parents=True, exist_ok=True)
    (SKILLS / "postcard-design").mkdir(parents=True, exist_ok=True)
    (SKILLS / "outreach" / "SKILL.md").write_text(outreach + "\n")
    (SKILLS / "postcard-design" / "SKILL.md").write_text(postcard + "\n")
    print("wrote plugin/skills/outreach/SKILL.md and plugin/skills/postcard-design/SKILL.md")


if __name__ == "__main__":
    build()
