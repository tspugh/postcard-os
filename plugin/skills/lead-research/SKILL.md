---
name: lead-research
description: Discover and research local business leads through the postcard MCP — stage candidates, claim and research them to the quality bar, and network out from already-contacted leads into a web of researched prospects. Use when finding or researching businesses for the postcard pipeline.
---

<!-- GENERATED from server/guidance/ by scripts/build_plugin_skills.py — edit there, then `make build-skills`. -->

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

# Discovery strategy — building the web of leads

Discovery is your job; the app only receives staged leads. There are two modes. Prefer
networking out once the pipeline has any history at all — it produces warmer, better-fitting
leads than cold sweeps.

## Mode 1 — network out from the pipeline you already have (preferred)

Every researched or contacted business is a node in a local web; its record is full of edges
to businesses nobody has staged yet. Work the web:

1. **Pull the existing web:** `postcard_list_businesses` (filter by `status="researched"`,
   and check the campaign board for contacted/interested participations). Each record carries
   the seeds: website, evidence URLs, address, service area, hooks.
2. **Follow the edges from each node:**
   - **Physical neighbors** — same plaza, strip, or street as the business's address
     ("businesses near {address}"). Postcard audiences are geographic; neighbors share one.
   - **Named relationships** — partners, suppliers, and "friends of the shop" mentioned on
     their site, in their reviews, or in local news that an evidence URL surfaced.
   - **Shared directories** — the chamber-of-commerce page, association roster, or "best of
     {market}" list where you found one lead always lists more.
   - **Customer-overlap categories** — a researched roofer implies the same homeowners need
     gutters, landscaping, HVAC. Fill categories the card still needs from the same audience.
3. **Stage what clears the bar** (name + category + working website), citing the connection
   in the lead's `note` (e.g. "two doors from Acme Roofing on Sagamore Pkwy"). The note is
   how the operator sees the web you are building.
4. **Research the new nodes**, and the web grows — each researched lead is the next round's
   seed.

## Mode 2 — cold sweep (when the pipeline is empty or a category has no thread to pull)

Search the seed market directly per category from settings: maps results, "{category}
{market}", local directories, review sites. Stage everything that clears the bar; volume is
fine, the staging bar is the filter.

## Always capture where the business operates

Proximity is the product's geography: every business on the card shares one audience, so
*where a lead's customers are* is research data, not trivia.

- During research, record the **street address** and the **service area** (the area whose
  residents the business serves or draws from — e.g. "Tippecanoe County", "downtown
  Lafayette", "20-mile radius of West Lafayette") via `postcard_update_business`
  (`address`, `service_area`). Do this even though the research bar does not require it.
- When choosing what to stage next, prefer candidates whose audience overlaps the web you
  already have — same neighborhoods, same service radius. Grouping leads by proximity makes
  every slot on the card reinforce the others.

## Discipline

- Never re-stage what exists: `postcard_stage_leads` rejects duplicates and disqualified
  records by name — read the rejection, work the existing record instead.
- Never network out from a disqualified lead; that thread is cut.
- A connection is a reason to *stage*, not a hook. Hooks still come from researching the
  business itself.

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
