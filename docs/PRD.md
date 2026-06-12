# PRD — Local Business Postcard Campaign Platform (MVP)

**Status:** Draft v3 (post-reconciliation with founder spec) · **Owner:** You & Grant · **Phase:** 1 (single-operator MVP)
**Seed market:** Lafayette, Indiana · **Default slot price:** $299/month

---

## Problem Statement

Local businesses struggle to find affordable, low-effort advertising. Shared-mail postcards (8 businesses on one card, one per industry) solve this for the advertiser, but running such a campaign is grinding manual work for the operator: finding candidate businesses in a market, researching each one, writing personalized outreach, tracking who replied and who committed, negotiating price, managing the waitlist when a category fills, collecting assets, and laying out the card. Today that work lives in spreadsheets, inboxes, and someone's head — it doesn't scale past one campaign, and nothing learned (who participated, who waitlisted, what outreach worked, what they paid) carries forward to the next one.

## Solution

A single-operator web application plus an MCP server that lets an AI agent (Claude, via a plugin) do the heavy lifting while the human stays in control of everything that leaves the building.

The system is a **lead pipeline with the agent as the worker and the human as the reviewer**:

- The agent finds and stages candidate businesses, researches them one at a time, and drafts personalized outreach emails — tailored using the operator's own business profile, tone preferences, and email expectations, which live in settings and are served to the agent as resources.
- The operator reviews drafts in a dashboard, leaves comments (or edits directly — an operator edit is just the next version), and clicks **Approve**. In phase 1 the operator copies the approved email, sends it from their own inbox, and marks it sent. **In phase 2, Approve pushes the approved version into the operator's Gmail as a draft — the system never sends and never holds send permission; the operator always pulls the trigger from their own mail client.** Inbox ingestion later turns the record into a tracked conversation chain (replies ingested, statuses advanced).
- Businesses are independent of campaigns. A **campaign** is one postcard run (market + month + deadline + category-exclusive slots); attaching a business to a campaign creates a **participation**, which carries the outreach status, the money (asking price vs. negotiated commitment, payment method), the **waitlist position** when a category is already won, and the **fulfillment checklist** (logo, offer, artwork) once committed.
- **Multiple campaigns may run concurrently, including in the same month.** Month is a label on the run, not a uniqueness key — two cards can ship in the same month (e.g. different neighborhoods, a second themed card, or overlapping fill windows). Category exclusivity is always **per campaign**, never per month. The operator can create a campaign at any time from the campaign view (name optional — defaults to "market + month"); where the dashboard or an agent tool needs "the" campaign without being told which (summary strip, `postcard_get_campaign_status` default), it uses the most recently created active campaign, and agents working multiple active campaigns must pass an explicit `campaign_id`.
- **Waitlists are preserved revenue.** When a category fills, additional interested advertisers are waitlisted in order — promoted if the winner cancels, and carried forward as priority prospects for the next campaign. Nothing interested is ever thrown away.
- The postcard is composed from structured per-slot content inside a versioned layout template, rendered safely in the dashboard, and iterated through the same comment loop as emails. (Future phases generate final artwork from the same structure.)
- A settings page is the human control panel: default price, category vocabulary, seed market, the operator's own business profile, and outreach style instructions. The agent reads all of it, so pricing, taxonomy, and voice stay consistent without repetition.
- Every agent action is logged to a visible activity feed, and the dashboard opens with a summary strip answering "what needs attention today."

The MCP tool surface *is* the workflow: each tool is a transition in the lead state machine, which keeps the agent's autonomy bounded by construction (nothing sends without a human, nothing active can be deleted, every disqualification carries an auditable reason).

## Lead Quality Bars

*These definitions are normative. They are encoded in the MCP resources and skills so the agent applies them mechanically.*

**Staging bar — what it takes to enter the pipeline.** A staged lead must have: a business **name**, a **category** tag, and a **working website URL**. The URL is the proof-of-existence test: if the agent (or operator) cannot point to a live web presence — site, Google Business profile, or active social page — the business is not stageable. Email is *not* required at staging; finding contact information is research work, not discovery work.

**Research bar — what it takes to be pitch-ready (`researched`).** At least one **contact** with an email or phone (with the source recorded and a confidence level), a **premise**, at least one **hook**, and at least one **evidence URL**.

- **Premise** (one per business, stable): a 2–3 sentence factual orientation — what the business does and for whom (e.g., "residential roofing contractor serving Tippecanoe County; primarily asphalt shingle replacement and storm repair"). The premise is what makes an outreach email coherent and lets the operator verify category fit.
- **Hooks** (a list, opportunistic): specific personalization ammunition — "family-owned 22 years," "4.9★ across 210 Google reviews," "just opened a second location." Hooks are what separate a reply-worthy email from spam.

**Disqualification — when a lead exits.** A lead is disqualified with a reason code + free-text note. The codes are a closed vocabulary so the agent's judgment is auditable:

| Code | Meaning |
|---|---|
| `no_contact_info` | Research exhausted; no email or phone findable |
| `defunct` | Closed, no longer operating, or website dead |
| `bad_fit` | Not local to the market, national chain, or doesn't match any campaign category |
| `duplicate` | Same business already in the pipeline |
| `do_not_contact` | Operator marked off-limits |
| `other` | Anything else — note required |

**Active is protected.** A business with an active participation (`prospecting` through `paid`) cannot be disqualified, and its last reachable contact cannot be deleted — corrections go through edits, not removal. Disqualified leads stay in the database (never re-staged, never re-researched) but collapse out of working views.

## User Stories

### Operator (Grant)

1. As an operator, I want a settings page holding the default slot price, so that the agent and all outreach use consistent pricing without me restating it.
2. As an operator, I want the settings page to hold the category vocabulary (seeded with the canonical 8: roofer, plumber, electrician, HVAC, landscaper, auto repair, realtor, restaurant), so that lead tagging and campaign slots draw from a shared, editable taxonomy.
3. As an operator, I want the settings page to hold the seed market (Lafayette, IN), so that the agent scopes research without being told each session.
4. As an operator, I want to record **my own business's details** (name, what we do, personal notes, signature) in settings, so that the agent has sender context and can tailor emails with personal touches — and so that my business can appear on the card too.
5. As an operator, I want to set a **base email tone and editable outreach instructions** in settings, so that the agent writes the way I would and I can tune it over time without touching code.
6. As an operator, I want a **dashboard summary strip** (spots filled/remaining, revenue committed vs. collected, drafts awaiting review, waitlist count, deadline countdown), so that the home screen answers "what needs attention today" at a glance.
7. As an operator, I want to manually stage leads (paste a name/category/website list), so that businesses I already know enter the same pipeline the agent uses.
8. As an operator, I want a pipeline board showing every lead by state, so that I can see at a glance what's staged, being researched, contacted, interested, waitlisted, committed, or declined.
9. As an operator, I want each lead card to show **when it was created and whether I've viewed it yet**, so that new agent-generated leads are obvious and nothing slips by unseen.
10. As an operator, I want a detail view per business showing its research (premise, hooks, evidence links), so that I can spot-check the agent's claims before they reach an email.
11. As an operator, I want a business to hold **zero or more contacts** (name, email + source + confidence, phone, title), so that a business can exist before a contact is found and can have multiple people attached.
12. As an operator, I want each business tagged with a category (what kind of good/service they sell), so that I can compose a campaign with variety and enforce category exclusivity.
13. As an operator, I want to see the full email thread per participation with version history, so that I can follow how a draft evolved in response to my feedback.
14. As an operator, I want to leave comments on an email draft **or edit it directly** (my edit becomes the next version, attributed to me), so that small fixes don't require a feedback round-trip.
15. As an operator, I want an **Approve** button on an email draft, so that approval is an explicit, recorded state change — and, in phase 2, the trigger that places the approved email into my Gmail drafts.
16. As an operator, I want a **Copy** button and a **Mark Sent** button on an approved email, so that phase-1 manual sending from my own inbox is two clicks, not retyping.
17. As an operator, I want to add a business to a campaign (creating a participation in a category) and remove it again, so that leads are never permanently bound to one campaign.
18. As an operator, I want to record the committed amount when a business agrees (which may differ from asking price), so that negotiation outcomes are captured per campaign.
19. As an operator, I want to record **payment status, method, and date** (cash, PayPal, other) on a committed participation, so that money owed vs. money collected is always visible without a payments integration.
20. As an operator, I want additional interested advertisers in a full category to be **waitlisted in order**, so that excess demand is preserved instead of declined.
21. As an operator, I want to **reorder the waitlist manually and promote** a waitlisted advertiser when a slot frees up (cancellation or decline), so that the next-in-line rule is the default but I keep final say.
22. As an operator, I want waitlisted advertisers from a completed campaign to surface as **priority prospects when composing the next campaign**, so that future revenue carries forward.
23. As an operator, I want a **fulfillment checklist per committed advertiser** (logo received, offer confirmed, artwork approved), so that "ready to print" is a roll-up of facts, not a feeling.
24. As an operator, I want the campaign view to show all category slots with fill status, waitlist depth, deadline, and a scarcity counter ("5 of 8 filled, closes Friday"), so that I can mirror that urgency in conversations.
25. As an operator, I want the campaign view to total committed and collected dollars, so that I know whether the card is worth printing.
26. As an operator, I want to see a rendered preview of the postcard draft, so that I can judge the design without leaving the dashboard.
27. As an operator, I want to comment on a specific postcard slot, so that feedback like "make the plumber's offer bigger" is anchored to the thing it's about.
28. As an operator, I want to disqualify a lead with a reason code, so that dead ends don't clutter the pipeline and the agent doesn't re-research them — and I want active advertisers to be protected from disqualification or deletion.
29. As an operator, I want an **agent activity feed** showing every agent action (and, later, every scheduled run) with timestamps, so that I always know when the agent ran and what it did.
30. As an operator, I want to see which businesses participated in — or were waitlisted for — past campaigns, so that re-pitching next month starts from history instead of zero.
31. As an operator, I want campaigns to be archived, never deleted, so that history is permanent.
32. As an operator, I want the whole system to start with one command on a private machine, so that running campaign #1 requires no infrastructure work and no login (auth is phase 2).

### Agent (Claude via plugin + MCP)

33. As an agent, I want a single orientation tool returning campaign status *and* settings (price, categories, market, sender profile, outreach instructions) *and* waitlist state, so that every session starts with correct context in one call.
34. As an agent, I want **step-by-step workflow instructions served as resources** — the state machines, the quality bars, which tool to call when — so that even starting with minimal context I can work the pipeline correctly.
35. As an agent, I want **clear, written expectations for what a good email looks like** (tone, structure, the operator's instructions and sender profile), so that drafts are right the first time and feedback rounds shrink.
36. As an agent, I want to stage leads I found through web research with the minimal staging bar (name, category, website), so that broad discovery is cheap and fast — and I want the tool to reject sub-bar leads with an explanation.
37. As an agent, I want to claim a staged lead exclusively, so that two sessions never duplicate research work.
38. As an agent, I want to submit structured research (contacts + premise + hooks + evidence URLs), so that drafts are grounded and the operator can verify claims.
39. As an agent, I want **CRUD tools for business details and contacts** (update fields, add/correct/remove a contact), so that I can keep records accurate as I learn more — with guardrails that protect active advertisers.
40. As an agent, I want to disqualify a lead with a reason code from the defined vocabulary, so that the pipeline reflects reality and my judgment is auditable.
41. As an agent, I want to save an email draft that is automatically versioned and placed in review, so that nothing I write is sendable without human approval.
42. As an agent, I want to read operator comments on a draft, so that my next version responds to specific feedback.
43. As an agent, I want to **move an interested advertiser to the waitlist when their category is already won** — and I want the commitment tool to tell me to do exactly that when exclusivity blocks me — so that excess demand is captured instead of erroring out.
44. As an agent, I want to save postcard content per slot as structured JSON within a versioned template, so that I cannot break the card's layout while iterating on one advertiser.
45. As an agent, I want to read per-slot postcard comments, so that design feedback routes to the exact slot it concerns.
46. As an agent, I want reference material (workflow, quality bars, slot spec, template, pricing, sender profile, outreach style) available as MCP resources, so that stable knowledge doesn't consume tool calls.
47. As an agent, I want actionable error messages from every tool (what failed, what to do instead), so that I can self-correct instead of stalling.
48. As an agent, I want to record a commitment amount on a participation when the operator relays a "yes," so that pipeline money state can be updated in the flow of conversation.

## UI Requirements

*Four screens. This section is also the manual-test checklist: before each milestone, walk every line below. Single user, no auth in phase 1 (runs on localhost or a private box).*

**Global expectations**
- Every entity produced by the agent (email draft, postcard slot) is commentable; comments show author and timestamp and can be marked resolved.
- Every state change (approve, mark sent, commitment, waitlist move, promotion, disqualify) is timestamped and visible in the relevant detail view.
- The current campaign's scarcity status (slots filled / total, deadline) is visible from any screen (e.g., header badge).
- No action in the UI sends email or spends money. The riskiest UI action is a state flip.
- Visual direction (recorded, not engineered-for): fast, minimal clicks, keyboard-friendly, modern-SaaS feel (Linear/Notion register); dark mode is a welcome default but not a phase-1 requirement.

**1. Pipeline (home)**
- **Summary strip** across the top: spots filled/remaining for the active campaign, revenue committed vs. collected, drafts awaiting review, waitlist count, deadline countdown, overdue/unviewed counts.
- Board of leads grouped by state: Staged → Researching → Researched → Contacted → Interested → Waitlisted → Committed, with Disqualified/Declined collapsed to the side.
- Each card shows business name, category tag, created date, an **unviewed badge** if the operator hasn't opened it, and (if attached) campaign + asking price. Opening a card clears the badge.
- Clicking a card opens a detail drawer: premise, hooks, evidence links opening in a new tab; the **contacts list** (add/edit/remove a contact: name, email + source + confidence, phone, title — delete blocked with explanation if it's the last contact on an active advertiser); category tag editor; the email thread (all versions, newest first, status + author badge per version); a comment box; an **Edit** affordance on the current in-review version (saves as next version, author = operator); **Approve**, **Copy**, and **Mark Sent** buttons enabled only in valid states (Approve only on `in_review`; Copy and Mark Sent only on `approved`); payment fields (status, method, date) and the **fulfillment checklist** once committed.
- Manual staging affordance: paste/enter multiple leads at once — name, category, **website (required)**; the staging bar is enforced with a clear message.
- A collapsible **agent activity feed** (most recent agent tool calls with timestamps and one-line summaries), so "did the agent run?" is answerable from the home screen.

**2. Campaign**
- **Create campaign** is always reachable from this view (not only when no campaign exists): optional name (auto-named "market + month" when blank), month + year as explicit dropdowns (native `<input type="month">` is unsupported in Firefox/desktop Safari and must not be used), and a deadline date. A campaign picker switches between runs; creating a new campaign selects it.
- Slot board: one row/tile per category from settings; shows empty / pitched (count of active participations) / committed (business name + amount + checklist progress) / **waitlist depth**.
- Per-category **waitlist panel**: ordered list, manual reorder (up/down), and a **Promote** action enabled only when the category slot is free (promotion requires entering the committed amount; exclusivity is enforced).
- Deadline countdown and scarcity counter; total committed and collected dollars for the campaign.
- Attach a researched business to the campaign in a category; detach a participation (blocked past `contacted`). Attaching snapshots the current default price as `asking_price`.
- Exclusivity surfaced here: attempting to mark a second business `committed` in an occupied category is blocked with a message offering waitlist instead. Multiple simultaneous *pitches* per category are allowed and expected.
- When composing a new campaign, prior-campaign **waitlisted and participated businesses surface as priority prospects** for one-click attach.
- Campaign lifecycle visible: Draft → Filling → Full → Fulfillment → Completed → Archived. Archive, never delete.
- Record/edit committed amount on a participation.

**3. Postcard**
- Sandboxed render (iframe, scripts disabled, sanitized fragments) of the current template populated with current slot JSON.
- Slot-level comment affordance (click a slot → comment thread for that slot).
- Draft version selector; notes per draft version.
- Empty slots render visibly as empty (with category label) rather than collapsing, so the operator sees the card as it would print today.

**4. Settings**
- Editable: default slot price, category vocabulary (add/remove/rename tags), seed market, default spot count for new campaigns.
- **My business**: name, description, personal notes for the agent, email signature.
- **Outreach style**: base tone selection plus free-text instructions ("what a good email looks like to me"). A note explains these are served to the agent verbatim.
- Changes apply to *future* snapshots only; a notice states that existing participations keep their captured `asking_price`.

## Implementation Decisions

- **Stack: MCP-centric (decision recorded vs. founder spec).** The agent is a *worker* operating the pipeline through an MCP server, not an AI feature embedded in the app. Python/FastAPI/FastMCP monolith; the founder spec's Next.js-with-AI-buttons architecture is explicitly not adopted. One repo: server, web, plugin folders; REST routes and MCP tools are thin wrappers over a shared service layer, the single home of all business rules.
- **Sending: Gmail drafts, never auto-send (decision recorded; adopts founder spec).** Review happens entirely in-app, pre-approval. Phase 1: Approve → Copy → operator sends from own inbox → Mark Sent. Phase 2: Approve additionally creates a Gmail draft via an OAuth scope limited to draft creation — the application never holds send permission, making "never sends automatically" a property enforced by credentials, not policy. One-way push, no sync-back: the approved version is canonical as-of-approval; post-approval edits in Gmail are the operator's prerogative and are not mirrored. Send-on-approve survives only as a possible opt-in mode in a much later phase.
- **Postcard module stays in phase 1 (decision recorded vs. founder spec).** Versioned template + structured slots + sandboxed render ship now; the structure is what makes future artwork generation and print pipelines additive.
- **Discovery is the agent's job (decision recorded vs. founder spec).** The app receives staged leads; it does not search. An optional phase-2 MCP tool may wrap a Places-style API for bulk discovery, feeding the same staging bar; the seed market in settings concentrates all discovery on the local city either way.
- **Five-entity core model.** `businesses` (campaign-independent; research and enrichment state) · `contacts` (zero-or-more per business) · `campaigns` (one postcard run; lifecycle Draft→Filling→Full→Fulfillment→Completed→Archived; archived, never deleted) · `participations` (outreach state, category, asking vs. committed price, payment fields, waitlist order, fulfillment checklist, slot assignment) · supporting tables (emails, comments, interactions, agent activity, postcard drafts).
- **Contacts are rows, not JSONB.** One business → many contacts, businesses creatable contact-less, and agent-side CRUD on individual contacts all demand row semantics.
- **Quality bars are enforced, not advisory.** Staging and research bars are validated by the tools themselves, with rejections that restate the bar. Disqualification uses the closed reason-code vocabulary. Duplicate staging is rejected naming the existing record; duplicates are never merged automatically (principle adopted from founder spec; fuzzy matching deferred).
- **Active is protected.** No disqualification of businesses with active participations; no deletion of the last contact on an actively-pitched business; participations detachable only in `prospecting`/`contacted`; campaigns archive instead of deleting.
- **Waitlist is a first-class status.** `waitlisted` sits in the outreach state machine with an order column per category. The exclusivity error *recommends* the waitlist move. Promotion re-runs the exclusivity check and requires a committed amount. Waitlisted businesses from prior campaigns surface as priority prospects for the next one.
- **Fulfillment is a checklist, not five statuses.** Logo received / offer confirmed / artwork approved live as a checklist on the committed participation; campaign "ready to print" is the roll-up. This covers the founder spec's post-paid pipeline stages without bloating the state machine.
- **Email versioning instead of a revise endpoint — now with two authors.** Saving a draft (agent tool or operator edit) creates the next version in `in_review`, attributed to its author. Approval and sending apply to a specific version. Sent versions are immutable. The participation is the conversation container, which is what makes the phase-2 evolution to full email chains a schema extension rather than a redesign.
- **Price snapshotting.** Default price lives in settings; attaching snapshots `asking_price`; negotiation lands in `committed_amount`; payment recording (`payment_method`, `paid_at`) is manual in phase 1. Settings changes never rewrite history.
- **Single-sourced agent guidance.** Workflow rules, quality bars, DQ vocabulary, email expectations, sender profile, and outreach style are served both as MCP resources and packaged into the plugin skills. One source, two delivery channels.
- **Agent activity logging is middleware.** Every MCP tool invocation is logged and surfaced in the UI feed; scheduled runs later land in the same feed.
- **Deployment:** docker-compose (Postgres + app server) on localhost or a single private EC2 box. No auth in phase 1. Postgres over SQLite — rationale in the tech design doc.

## Testing Decisions

- **Tests target external behavior at the highest seam: the service layer**, against a real Postgres in Docker. Both REST and MCP delegate here, so the state machines are tested once. Representative outcomes: staging without a website rejected; double-claim fails; research without contact/premise/hook/evidence rejected; second commitment in a category rejected with waitlist recommendation; waitlist ordering maintained and reorderable; promotion blocked while slot occupied, succeeds after decline; DQ blocked on active participation; last-contact delete blocked on active advertiser; operator edit creates next version with operator attribution; `asking_price` snapshot survives settings change.
- **MCP contract seam** via FastMCP's in-process client: validation errors are actionable and restate the relevant bar; read-only tools mutate nothing; orientation tool includes settings and waitlist state; every call logged. Supplemented by ~10 read-only agent evaluation questions (mcp-builder style).
- **HTTP seam** thin: FastAPI test client confirming dashboard contracts (including summary-strip roll-ups and checklist/payment patches).
- **Postcard render seam:** snapshot test of slot JSON → template → HTML; sanitization test proving hostile fragments are defanged.
- **UI is manually tested** against the UI Requirements section above, which serves as the checklist.

## Out of Scope (Phase 1)

- Sending email from the system in any form. Phase 2 adds **Gmail draft creation** (never sending); inbox reading, reply ingestion, follow-up management, and per-message chain UI come after that.
- Payments, invoicing, or money movement (status/method/date are recorded manually; no processor).
- Print-ready file export and mailing-list handling (provider-agnostic by design — import/export for USPS or mail houses is future work; no tight provider integration, per founder spec).
- **Postcard artwork generation** — a later, button-triggered step where the agent turns the approved structured draft into high-quality final art via an image-generation tool.
- **Tasks module** (due dates, priorities, overdue flags — founder spec feature): deferred; the activity feed, unviewed badges, and checklist cover phase-1 follow-up needs. Cheap table when it earns its place.
- **Global instant search and rich filters** (founder spec feature): deferred until data volume justifies it; the board + simple filters suffice for one market.
- **Fuzzy duplicate detection with approval queue** (founder spec feature): phase 1 uses exact-match rejection; the never-auto-merge principle is adopted now.
- **Analytics and pricing recommendations** (fill rate, time-to-fill, revenue by category/month; "if campaigns sell out fast, raise prices"): the data model captures all inputs from day one; analysis ships when there is history to analyze. The pricing philosophy is recorded in Further Notes so the intent survives.
- Authentication and external login (phase 2), multi-user, multi-tenant, advertiser portal, customer logins, or any SaaS features.
- Hosted/background agent, scheduled autonomous runs, self-hosted models (the activity feed is built ready to display them).
- Discord/SMS conversational gateway (phase 3, via Agent SDK).
- Optional Places-API discovery tool (phase 2).
- Upsells, recurring reservations, premium placements, territory management.

## Further Notes

- **Success for phase 1** is concrete: the agent stages and researches leads in Lafayette, drafts get approved through the comment/edit loop, Grant sends them from his own inbox, waitlists capture excess demand, at least one card's worth of pipeline (with payment and fulfillment state) is visible end-to-end, and a reviewable postcard draft exists.
- **Reconciliation with founder spec (Grant's "GR Postcard OS" doc):** four decisions were taken — (1) stack is MCP-centric Python/FastAPI, agent-as-worker, not Next.js with embedded AI; (2) sending adopts his Gmail-drafts-only philosophy, strengthened by scope-limited OAuth; (3) the postcard module ships in phase 1 despite his V1 exclusion, because the structured model is the cheap part and everything generative builds on it; (4) discovery belongs to the agent, with an optional in-app Places tool later. His waitlist, fulfillment stages, payment recording, campaign lifecycle, dashboard-as-daily-workspace, archive-never-delete, never-auto-merge, and configurable-everything principles are adopted. His final guiding principle is adopted verbatim: *every feature must reduce administrative work while keeping the owner in complete control.*
- **Pricing philosophy (adopted from founder spec):** if campaigns consistently fill quickly, pricing should increase; a future analytics phase should recommend adjustments from historical fill data.
- **Email deliverability** stays a human problem through phase 2 by design — Grant's own Gmail sends every message, so domain reputation, SPF/DKIM, and spam-filter risk never become ours until volume demands it.
- **Phase 2 candidates,** in rough order of value: Gmail draft creation on Approve, inbox ingestion and the email-chain UI, basic login, Places discovery tool, outreach analytics, print/mailing-list export, postcard artwork generation, tasks, global search, fuzzy dedupe.
- The roadmap's later phases (hosted agent for non-BYOA users, SaaS multi-tenancy) reuse this exact service layer; nothing in phase 1 is throwaway.

