---
name: campaign-outreach
description: Compose a postcard campaign from researched businesses and draft outreach emails for human review — attach leads, draft and revise versioned emails, record commitments, and use waitlists when categories fill. Use when working a campaign or writing outreach.
---

<!-- GENERATED from server/guidance/ by scripts/build_plugin_skills.py — edit there, then `make build-skills`. -->

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

0. **Discover** — find candidates per `postcard://reference/research-strategy`: network out
   from already-researched and contacted businesses (`postcard_list_businesses` is the read
   tool) before cold-searching the market, and capture each lead's address and service area
   while researching.
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
