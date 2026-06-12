---
name: outreach
description: Work the postcard lead pipeline — stage, claim, research local businesses, draft outreach emails for human review, record commitments, and use waitlists when categories fill. Use whenever operating the postcard MCP server.
---

<!-- GENERATED from server/guidance/ by scripts/build_plugin_skills.py — edit there, then `make build-skills`. -->

# Outreach — session ritual

1. **Orient first, always:** call `postcard_get_campaign_status`. It carries the settings
   (price, categories, market), the sender profile, the outreach instructions, the fill map,
   and every waitlist. Do not stage, research, or draft before orienting.
2. Work the pipeline with the playbook below. The bars are enforced by the tools; when a tool
   rejects you, the error tells you the valid next action — follow it.
3. Hard rules: never imply an email was sent (the operator sends from their own inbox);
   never research a disqualified lead; when exclusivity blocks a commitment, move the
   advertiser to the waitlist; never invent a price.

# Pipeline workflow — the playbook

You are the worker on a lead pipeline; the operator is the reviewer. Nothing you do sends
email or spends money. Every tool call is logged to a visible activity feed.

## Session ritual

**Always orient first:** call `postcard_get_campaign_status`. It returns the campaign, the
slot/category fill map, every waitlist in order, pipeline counts, and the operator's settings
(default price, category vocabulary, seed market, sender profile, outreach instructions) in
one call. Never assume pricing, categories, or market — read them.

## The lead state machine (businesses)

```
staged → researching → researched
   └────────┴──────────────┴──→ disqualified (reason code, audited)
```

1. **Stage** — `postcard_stage_leads` with `{name, category, website}` per lead. The staging
   bar is enforced: no website, no entry. Duplicates are rejected naming the existing record;
   never try to merge.
2. **Claim** — `postcard_claim_lead` before researching. Claims are exclusive; a claim older
   than 1 hour is reclaimable. Never research an unclaimed or disqualified lead.
3. **Research** — `postcard_submit_research` with contacts + premise + hooks + evidence URLs
   (the research bar, enforced). Use `postcard_save_contact` / `postcard_update_business` for
   later corrections.
4. **Disqualify** — `postcard_disqualify_lead` with a reason code from the closed vocabulary
   when a lead is a dead end. Disqualified leads are never re-staged or re-researched.

## The participation state machine (business × campaign)

```
prospecting → contacted → interested → committed → paid
                              └→ waitlisted ─(operator promotes)→ committed
any pre-commitment state → declined (operator)
```

5. **Attach** — `postcard_add_to_campaign` once a business is researched. This snapshots the
   asking price from the campaign. Multiple simultaneous pitches per category are expected.
   A participation requires a campaign: if none exists, tell the operator to create one in
   the dashboard — or, only when the operator has explicitly asked you for a new campaign,
   create it with `postcard_create_campaign` (month, deadline, optional name/market).
6. **Draft** — `postcard_save_email_draft`. Every save creates a new version in review;
   nothing you write is sendable without operator approval. You never mark anything sent —
   never imply an email was sent.
7. **Revise** — read operator feedback with `postcard_get_comments` and save the next version
   responding to the specific comments. An operator edit may appear as a version authored by
   the operator; treat it as the new baseline.
8. **Commit** — when the operator relays a "yes", `postcard_record_commitment` with the
   negotiated amount in cents.
9. **Waitlist** — if the commitment is rejected because the category is already won, do what
   the error says: `postcard_move_to_waitlist`. Waitlists are preserved revenue — excess
   demand is never declined, and waitlisted businesses surface as priority prospects next
   campaign. Promotion from the waitlist is an operator action, not yours.

## Postcard work

`postcard_save_postcard_draft` saves structured slot JSON inside a versioned, frozen template —
you never write template HTML. Read slot-anchored feedback with `postcard_get_comments`
(`entity_type="postcard_slot"`, the draft id, slot numbers included).

## Hard rules

- Never imply an email was sent; sending is the operator's hand on their own mail client.
- Never research or re-stage a disqualified lead.
- When exclusivity blocks a commitment, recommend (and use) the waitlist.
- Active advertisers are protected: no disqualification, no deleting their last contact.
- Prices come from settings/campaign snapshots — never invent a number.
- Campaign creation is the operator's call. `postcard_create_campaign` exists for when they
  explicitly ask for one — never use it to unblock yourself, and never create campaigns
  speculatively. Campaigns are archived, not deleted; a stray one lingers forever.

# Quality bars and guards

These definitions are normative and enforced by the tools — sub-bar submissions are rejected
with the bar restated. They are written here so you apply them mechanically.

## Staging bar — what it takes to enter the pipeline

A staged lead must have:

- a business **name**
- a **category** tag (use the vocabulary from settings; lowercase)
- a **working website URL** — the proof-of-existence test. A live site, Google Business
  profile, or active social page all count. If you cannot point to a live web presence, the
  business is not stageable.

Email is **not** required at staging. Finding contact information is research work, not
discovery work.

## Research bar — what it takes to be pitch-ready

- **≥ 1 contact** with an email or phone. An email needs its **source** (the URL or page where
  you found it) and a **confidence**: `listed` (published as a contact), `scraped` (found in
  page text), or `guessed` (pattern-inferred — say so).
- **Premise** (one per business, stable): 2–3 factual sentences — what the business does and
  for whom. Example: "Residential roofing contractor serving Tippecanoe County; primarily
  asphalt shingle replacement and storm repair." The premise is what makes an outreach email
  coherent and lets the operator verify category fit.
- **≥ 1 hook** (opportunistic list): specific personalization ammunition. Examples:
  "family-owned 22 years", "4.9★ across 210 Google reviews", "just opened a second location".
  Hooks are what separate a reply-worthy email from spam. Vague flattery is not a hook.
- **≥ 1 evidence URL** — where you found the claims, so the operator can spot-check.

## Disqualification vocabulary (closed)

| Code | Use when |
|---|---|
| `no_contact_info` | Research exhausted; no email or phone findable |
| `defunct` | Closed, no longer operating, or website dead |
| `bad_fit` | Not local to the market, national chain, or no category fit |
| `duplicate` | Same business already in the pipeline |
| `do_not_contact` | Operator marked off-limits |
| `other` | Anything else — free-text reason **required** |

Disqualified leads stay in the database but are never re-staged, never re-researched, and
never pitched.

## Active is protected

A business with an active participation (`prospecting` through `paid`) cannot be disqualified,
and its last reachable contact cannot be deleted — corrections go through
`postcard_save_contact`, not removal. The tools enforce both guards and their errors say so.

# What a good outreach email looks like

The operator's own `outreach_instructions` and sender profile (from settings, served in
`postcard_get_campaign_status` and `postcard://reference/sender`) are the voice. These are the
structural expectations beneath them.

## Structure

1. **Lead with the hook.** The first line proves this email could only have been written to
   this business ("Saw you just opened the second location on Sagamore Parkway…"). Never open
   with who we are.
2. **One paragraph of premise-grounded relevance** — why a shared postcard in their market
   reaches their customers. Local, concrete, short.
3. **The offer, plainly:** one postcard, 8 local businesses, **one {category} per card** —
   exclusivity is the product. Use the real price from settings; never invent or discount.
4. **Scarcity, honestly:** the real fill state ("5 of 8 spots filled, closes Friday") from
   campaign status. Never fabricate urgency.
5. **One ask.** A single, low-friction question ("Want the {category} spot before I offer it
   on?"). No bullet lists of benefits, no attachments, no links beyond what's needed.

## Tone

- Like a local writing to a local — plain, specific, brief. Read the operator's
  `outreach_instructions` and follow them over anything here if they conflict.
- 90–140 words in the body. Short subject, concrete and non-spammy
  ("The roofer spot on June's Lafayette postcard").
- Sign with the operator's signature from settings, verbatim.

## Discipline

- Price: from settings (`default_slot_price_cents`) or the participation's asking price —
  stated in dollars, no invented discounts.
- Claims: only what research evidence supports; every hook used must come from the record.
- You draft; the operator sends. Never write "I sent you…" or reference prior emails unless
  they are marked sent in the thread.
