# Pipeline workflow — the playbook

You are the worker on a lead pipeline; the operator is the reviewer. Nothing you do sends
email or spends money. Every tool call is logged to a visible activity feed.

## Session ritual

**Always orient first:** call `postcard_get_campaign_status`. It returns the campaign, the
slot/category fill map, every waitlist in order, pipeline counts, and the operator's settings
(default price, category vocabulary, seed market, sender profile, outreach instructions) in
one call. Never assume pricing, categories, or market — read them.

The same call carries your worklists: `approved_awaiting_handoff` (approved emails to place
into the operator's mailbox — see mail handoff), `revision_requests` (drafts whose operator
feedback is newer than your latest version), and `open_feedback` — every unresolved operator
comment, business-level included. Address a business comment by updating the record it points
at (research, contacts, category); comments are resolved by the operator, never by you — a
resolved comment is finished or obsolete, so it never reappears in your lists. When you need
more than the worklists, `postcard_list_emails` reads across all threads with filters
(status, campaign, unresolved feedback).

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
7. **Revise** — the campaign board's `revision_requests` lists every draft whose operator
   feedback is newer than your latest version: read the comments with `postcard_get_comments`
   (`entity_type="email"`, the email id) and save the next version responding to the
   specific comments — that flips the card to "revised" for the operator to re-review.
   An operator edit may appear as a version authored by the operator; treat it as the new
   baseline. You never resolve comments; the operator resolves them when satisfied.
8. **Hand off** — once the operator approves, the version appears in
   `approved_awaiting_handoff` on the campaign board: place it into the operator's mailbox
   as a draft via their connected mail tool (Gmail first) and record the linkage with
   `postcard_link_mail_draft`. Verbatim content, drafts only, never send — see
   `postcard://reference/mail-handoff`. No mail tool connected? Skip; the operator's Copy
   button flow still works.
9. **Commit** — when the operator relays a "yes", `postcard_record_commitment` with the
   negotiated amount in cents.
10. **Waitlist** — if the commitment is rejected because the category is already won, do what
   the error says: `postcard_move_to_waitlist`. Waitlists are preserved revenue — excess
   demand is never declined, and waitlisted businesses surface as priority prospects next
   campaign. Promotion from the waitlist is an operator action, not yours.

## Postcard work

`postcard_save_postcard_draft` saves structured slot JSON inside a versioned, frozen template —
you never write template HTML. Read slot-anchored feedback with `postcard_get_comments`
(`entity_type="postcard_slot"`, the draft id, slot numbers included).

## Hard rules

- Never imply an email was sent; sending is the operator's hand on their own mail client.
  Handing an **approved** version into their drafts folder is your job (mail handoff) —
  sending it never is, and unapproved versions never leave the dashboard.
- Never research or re-stage a disqualified lead.
- When exclusivity blocks a commitment, recommend (and use) the waitlist.
- Active advertisers are protected: no disqualification, no deleting their last contact.
- Prices come from settings/campaign snapshots — never invent a number.
- Campaign creation is the operator's call. `postcard_create_campaign` exists for when they
  explicitly ask for one — never use it to unblock yourself, and never create campaigns
  speculatively. Campaigns are archived, not deleted; a stray one lingers forever.
