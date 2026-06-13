# Technical Design — Postcard Campaign Platform (MVP)

Companion to the PRD (v3). This document is the build reference: architecture, schema, state machines, MCP surface, rendering, and deployment. It changes at implementation speed; the PRD changes at product speed.

---

## 1. Architecture

```
┌─────────────────────────── one repo ───────────────────────────┐
│                                                                │
│  web/            React (Vite) SPA — 4 screens                  │
│    └── talks REST to server                                    │
│                                                                │
│  server/         FastAPI app (one process)                     │
│    ├── /api/*    REST routes (dashboard contract)              │
│    ├── /mcp      FastMCP mounted ASGI app (agent contract)     │
│    ├── services/ ALL business rules live here                  │
│    ├── guidance/ single-source markdown: workflow, bars,       │
│    │             email expectations → served as MCP resources  │
│    │             AND packaged into plugin skills at build      │
│    └── models/   SQLAlchemy + Alembic migrations               │
│                                                                │
│  plugin/         Claude plugin                                 │
│    ├── manifest → points at server /mcp                        │
│    └── skills/   outreach/, postcard-design/ (generated from   │
│                  guidance/ + skill-specific framing)           │
│                                                                │
│  docker-compose.yml   postgres + server (+ web dev server)     │
└────────────────────────────────────────────────────────────────┘
```

Principles:

- **REST and MCP are both thin.** A route or tool parses input, calls one service function, formats output. No business logic outside `services/`.
- **FastMCP mounts into FastAPI** (`app.mount("/mcp", mcp_app)` with combined lifespans), so one process serves both contracts. Streamable HTTP transport; stateless.
- **Single-sourced guidance.** Workflow rules, quality bars, DQ vocabulary, and email expectations live once in `guidance/` (plus operator-editable settings fields) and are delivered twice: as MCP resources for any client, and baked into the plugin skills for Claude. Tool descriptions cite the same bars so there is exactly one definition of "stageable" anywhere in the system.
- **Agent activity middleware.** A FastMCP middleware logs every tool invocation (tool name, args summary, outcome, timestamp) to `agent_activity`; the dashboard feed reads it. Future scheduled runs log to the same table.
- **MCP-app readiness** is a discipline, not a feature: every dashboard view hydrates from a single REST endpoint returning one JSON document, so any view can later be repackaged as an MCP App resource.

Stack: Python 3.12, FastAPI, FastMCP, SQLAlchemy 2 + Alembic, Postgres 16, React + Vite, server-side sanitize via `nh3`, client-side DOMPurify.

**Decision vs. founder spec:** the founder doc proposed Next.js/TypeScript/Prisma with AI as an embedded feature. Not adopted — the agent here is a *worker* driving the pipeline through MCP, so the MCP server is the spine and the stack serves it first. The web app is deliberately a thin SPA over the same services.

### Why Postgres (and the SQLite alternative)

SQLite would genuinely suffice for a single operator: one file, zero containers, JSON1 covers our JSON needs, and it even supports the partial unique index used for category exclusivity. Its costs here: no native enums (CHECK constraints instead), single-writer semantics (acceptable at this scale with WAL, but the agent and dashboard do write concurrently), and a migration tax when leaving.

Decision: **Postgres.** Deployment is docker-compose regardless, so SQLite would save one container rather than any operational burden — while every later phase (background agent, inbox ingestion, multi-user, hosted) assumes Postgres. SQLAlchemy keeps the service layer portable, so this decision is reversible; revisit only if a zero-Docker `pip install && run` distribution becomes a goal. (A managed-Postgres host like Supabase slots in with no schema changes if self-hosting ever becomes unwanted.)

## 2. Schema

Conventions: UUID PKs, `created_at`/`updated_at` timestamptz on everything (omitted below), money as integer cents, enums as Postgres enums.

```sql
-- Single-row control panel (enforced by id check)
CREATE TABLE settings (
  id                       boolean PRIMARY KEY DEFAULT true CHECK (id),
  default_slot_price_cents integer NOT NULL DEFAULT 29900,
  default_total_slots      integer NOT NULL DEFAULT 8,
  categories               jsonb   NOT NULL,  -- ["roofer","plumber",...]
  seed_market              text    NOT NULL DEFAULT 'Lafayette, IN',
  operator_business        jsonb,             -- {name, description, personal_notes, signature}
  outreach_instructions    text               -- base tone + "what a good email looks like"
);

CREATE TYPE enrichment_status AS ENUM
  ('staged','researching','researched','disqualified');

CREATE TYPE dq_reason_code AS ENUM
  ('no_contact_info','defunct','bad_fit','duplicate','do_not_contact','other');

CREATE TABLE businesses (
  id                 uuid PRIMARY KEY,
  name               text NOT NULL,
  category           text NOT NULL,          -- tag from settings vocabulary (not FK; vocabulary is advisory)
  website            text NOT NULL,          -- STAGING BAR: proof of real business; tool rejects without it
  address            text,
  service_area       text,
  premise            text,                   -- factual orientation, one per business: what they do, for whom.
                                             -- e.g. "residential roofer serving Tippecanoe Co.; shingle replacement"
  hooks              jsonb,                  -- personalization ammunition, a list:
                                             -- ["family-owned 22 yrs", "4.9★ (210 reviews)"]
  evidence_urls      jsonb,                  -- URLs the agent used; operator spot-checks these
  status             enrichment_status NOT NULL DEFAULT 'staged',
  dq_code            dq_reason_code,
  dq_reason          text,                   -- required when dq_code = 'other'
  source             text,                   -- 'agent:web' | 'operator' | ...
  claimed_at         timestamptz,            -- set by claim; cleared on submit/DQ
  operator_viewed_at timestamptz             -- null ⇒ "unviewed" badge in UI; set when operator opens detail
);

-- Zero or more contacts per business; a business can exist contact-less.
-- Rows (not JSONB) because the agent needs per-contact CRUD and a business
-- has independent people that change at different times.
CREATE TABLE contacts (
  id               uuid PRIMARY KEY,
  business_id      uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  name             text,
  title            text,                     -- 'owner', 'office manager', ...
  email            text,
  email_source     text,                     -- URL or "site contact page"
  email_confidence text,                     -- 'listed' | 'scraped' | 'guessed'
  phone            text,
  is_primary       boolean NOT NULL DEFAULT false,
  CHECK (email IS NOT NULL OR phone IS NOT NULL)
);
CREATE UNIQUE INDEX one_primary_contact
  ON contacts (business_id) WHERE is_primary;

-- Lifecycle: archived, never deleted (founder principle).
CREATE TYPE campaign_status AS ENUM
  ('draft','filling','full','fulfillment','completed','archived');

CREATE TABLE campaigns (
  id                uuid PRIMARY KEY,
  name              text NOT NULL,            -- "Lafayette June 2026"
  market            text NOT NULL,
  month             date NOT NULL,
  deadline          date NOT NULL,
  slot_price_cents  integer NOT NULL,         -- snapshot of settings default at creation
  total_slots       integer NOT NULL,         -- snapshot of settings default at creation
  status            campaign_status NOT NULL DEFAULT 'draft'
);

CREATE TYPE outreach_status AS ENUM
  ('prospecting','contacted','interested','waitlisted','committed','paid','declined');

CREATE TABLE participations (
  id                     uuid PRIMARY KEY,
  campaign_id            uuid NOT NULL REFERENCES campaigns(id),
  business_id            uuid NOT NULL REFERENCES businesses(id),
  category               text NOT NULL,       -- copied from business at attach; editable
  status                 outreach_status NOT NULL DEFAULT 'prospecting',
  asking_price_cents     integer NOT NULL,    -- snapshot of campaign.slot_price_cents at attach
  committed_amount_cents integer,             -- live negotiated number; set at 'committed'/promotion
  payment_status         text,                -- 'pending' | 'paid' (manual phase-1 tracking)
  payment_method         text,                -- 'cash' | 'paypal' | 'check' | 'other'
  paid_at                timestamptz,
  waitlist_order         integer,             -- position within (campaign, category); null unless waitlisted
  fulfillment            jsonb NOT NULL DEFAULT '{}',
                                              -- {"logo_received":bool,"offer_confirmed":bool,"artwork_approved":bool,
                                              --  "logo_url":text} — unlocked at 'committed'
  slot_number            integer,             -- assigned when committed; 1..total_slots
  UNIQUE (campaign_id, business_id)
);
-- Exclusivity at commitment, enforced in DB as a backstop to the service rule:
CREATE UNIQUE INDEX one_committed_per_category
  ON participations (campaign_id, category)
  WHERE status IN ('committed','paid');
-- Waitlist ordering is dense per (campaign, category); service maintains it:
CREATE UNIQUE INDEX waitlist_position
  ON participations (campaign_id, category, waitlist_order)
  WHERE status = 'waitlisted';

CREATE TYPE email_status AS ENUM ('in_review','approved','sent','superseded');
CREATE TYPE email_author AS ENUM ('agent','operator');

-- Phase 1: versioned drafts of one outbound message per participation.
-- The PARTICIPATION is the conversation container. Phase 2a adds
-- gmail_draft_id (set when Approve pushes a Gmail draft — one-way, no sync-back;
-- the approved version is canonical as-of-approval). Phase 2b (chains) adds
-- direction ('outbound'|'inbound'), external_message_id, in_reply_to —
-- inbound replies join the same thread without redesign.
CREATE TABLE emails (
  id                uuid PRIMARY KEY,
  participation_id  uuid NOT NULL REFERENCES participations(id),
  version           integer NOT NULL,
  author            email_author NOT NULL,    -- operator edits create versions too
  subject           text NOT NULL,
  body              text NOT NULL,
  status            email_status NOT NULL DEFAULT 'in_review',
  approved_at       timestamptz,
  sent_at           timestamptz,
  UNIQUE (participation_id, version)
);
-- Saving version N+1 (either author) flips any prior 'in_review' version to 'superseded'.
-- 'approved' and 'sent' versions are never superseded or mutated.

CREATE TYPE comment_entity AS ENUM ('email','postcard_slot','business');

CREATE TABLE comments (
  id           uuid PRIMARY KEY,
  entity_type  comment_entity NOT NULL,
  entity_id    uuid NOT NULL,            -- email.id / postcard_drafts.id / business.id
  slot_number  integer,                  -- only for postcard_slot
  author       text NOT NULL,            -- 'grant' | 'agent'
  body         text NOT NULL,
  resolved     boolean NOT NULL DEFAULT false
);

CREATE TABLE interactions (
  id                uuid PRIMARY KEY,
  business_id       uuid NOT NULL REFERENCES businesses(id),
  participation_id  uuid REFERENCES participations(id),
  type              text NOT NULL,       -- 'email_sent','reply_received','waitlist_promoted','call', ...
  payload           jsonb,
  occurred_at       timestamptz NOT NULL
);

-- Every MCP tool invocation, written by middleware; UI activity feed reads it.
-- Scheduled/background runs (later phases) log here too — same feed, no new mechanism.
CREATE TABLE agent_activity (
  id           uuid PRIMARY KEY,
  tool_name    text NOT NULL,
  args_summary jsonb,                    -- redacted/truncated argument digest
  outcome      text NOT NULL,            -- 'ok' | 'rejected' | 'error'
  detail       text,                     -- one-line human summary for the feed
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE postcard_drafts (
  id           uuid PRIMARY KEY,
  campaign_id  uuid NOT NULL REFERENCES campaigns(id),
  version      integer NOT NULL,
  template_id  text NOT NULL DEFAULT 'grid-4x2-v1',  -- frozen template this draft targets;
                                                     -- alternate sectionings = new templates
  slots        jsonb NOT NULL,           -- array of slot objects (see §5)
  notes        text,
  UNIQUE (campaign_id, version)
);
```

## 3. State machines & quality bars (service-layer rules)

**Staging bar** (enforced by `stage_leads` and the UI): name + category + website URL. Leads missing any are rejected with a message restating the bar. Dedupe by (normalized name, market); duplicates surface as a rejection naming the existing record rather than silently merging. Never auto-merge.

**Business enrichment** — `staged → researching → researched | disqualified`

- `claim_lead`: only from `staged`; sets `researching` + `claimed_at`. A claim older than 1h is reclaimable (stale-claim recovery). Claiming a non-staged lead returns an actionable error naming its current state.
- `submit_research`: only from `researching`; **research bar**: ≥1 contact having email or phone (with source + confidence), premise, ≥1 hook, ≥1 evidence URL. Sets `researched`, clears claim. Contacts in the payload are created as `contacts` rows.
- `disqualify`: from `staged`, `researching`, or `researched`; requires a `dq_code` from the vocabulary (free-text `dq_reason` required when code is `other`). **Guard: refused if the business has any participation in an active status (`prospecting`–`paid`)** — the error says so and names the participation. Disqualified businesses are excluded from staging dedupe candidates and from `list_staged_leads`, and tools refuse to claim them.
- `delete_contact` **guard:** refused if it is the only email-or-phone-bearing contact on a business with an active participation; the error suggests `save_contact` to correct instead.

**Participation outreach** — `prospecting → contacted → interested → (committed | waitlisted) → paid | declined`

- Attach (`add_to_campaign`): business must be `researched`; snapshots `asking_price_cents`; starts `prospecting`. Detach allowed only in `prospecting`/`contacted`.
- `contacted`: set when an email on the participation is marked sent.
- `committed`: requires `committed_amount_cents`; service checks category exclusivity (the partial unique index is the backstop). Assigns `slot_number` from the free pool. **If the category is occupied, the rejection explicitly recommends `move_to_waitlist`.**
- `waitlisted`: from `interested` (or directly from a blocked commitment attempt); appended at the end of the (campaign, category) waitlist; `waitlist_order` is dense and service-maintained. Operator may reorder (REST). **Promotion** (operator action): allowed only when the category slot is free (winner `declined` or detached); requires a committed amount; runs the same exclusivity check; logs a `waitlist_promoted` interaction. Remaining waitlist closes up.
- **Carryover:** when composing a new campaign, businesses with `waitlisted` (or completed) participations in prior campaigns for the same market surface as priority prospects; attaching creates a fresh participation (businesses already outlive campaigns).
- `paid`: operator records `payment_status`/`payment_method`/`paid_at` (manual phase-1 tracking; no processor).
- Fulfillment checklist fields editable only at `committed`/`paid`. Campaign may move `full → fulfillment → completed` as slots commit and checklists complete; `archived` is terminal and reversible only by operator.
- Forward-only by default; the operator UI may correct state backward (logged as an interaction).

**Email versions** — `in_review → approved → sent`, with `in_review → superseded` when a newer version is saved **by either author** (agent via tool, operator via UI edit — attributed accordingly). Approve only from `in_review`; mark-sent only from `approved`. Phase 2a: Approve additionally creates a Gmail draft (see §7); the gate logic is unchanged.

## 4. MCP surface

Server name `postcard`. All tools return structured content; all errors are actionable (state the failed precondition — quoting the relevant quality bar or guard where applicable — and the valid next action). All invocations are logged to `agent_activity` by middleware.

| Tool | Args (essentials) | Effect | Annotations |
|---|---|---|---|
| `postcard_get_campaign_status` | `campaign_id?` (defaults to active) | Campaign, slot/category fill map, **per-category waitlists in order**, pipeline counts, deadline, **settings inline** (price, categories, market, sender profile, outreach instructions) | read-only |
| `postcard_create_campaign` | `month, deadline, name?, market?` | Create a campaign; name/market/price/slots default from settings. **Instruction-gated:** the tool description and workflow resource direct the agent to call it only on explicit operator request, never to unblock itself. When no campaign exists, campaign-dependent tool errors point to the dashboard and (gated) to this tool | non-destructive |
| `postcard_list_staged_leads` | `limit?` | Staged businesses awaiting research | read-only |
| `postcard_stage_leads` | `leads[] {name, category, website, note?}` | Bulk insert as `staged`; enforces staging bar; dedupes by (name, market) | non-destructive |
| `postcard_claim_lead` | `business_id` | `staged → researching`, exclusive | non-destructive |
| `postcard_submit_research` | `business_id, research{premise, hooks[], evidence_urls[], contacts[]}` | `researching → researched`; enforces research bar; creates contact rows | non-destructive |
| `postcard_update_business` | `business_id, fields{...}` | Partial update of auxiliary fields (address, service_area, premise, hooks, evidence, category) | non-destructive |
| `postcard_save_contact` | `business_id, contact{...}, contact_id?` | Upsert one contact (create or correct) | non-destructive |
| `postcard_delete_contact` | `contact_id` | Remove a contact; **guarded** (not the last reachable contact on an active advertiser) | destructive (guarded) |
| `postcard_disqualify_lead` | `business_id, dq_code, reason?` | → `disqualified`; code from closed vocabulary; **guarded** (no active participations) | non-destructive (guarded) |
| `postcard_add_to_campaign` | `campaign_id, business_id, category?` | Create participation, snapshot price | non-destructive |
| `postcard_remove_from_campaign` | `participation_id` | Delete participation (only in `prospecting`/`contacted`) | destructive (guarded) |
| `postcard_save_email_draft` | `participation_id, subject, body` | New version `in_review` (author = agent); supersedes prior in-review version | non-destructive |
| `postcard_get_comments` | `entity_type, entity_id, unresolved_only?` | Comments incl. slot numbers | read-only |
| `postcard_record_commitment` | `participation_id, amount_cents` | `→ committed` w/ exclusivity check; **rejection recommends waitlist** | non-destructive |
| `postcard_move_to_waitlist` | `participation_id` | `interested → waitlisted`, appended in order | non-destructive |
| `postcard_save_postcard_draft` | `campaign_id, slots[], template_id?, notes?` | New postcard draft version | non-destructive |
| *(phase 2)* `postcard_discover_businesses` | `area, category, limit?` | Places-style bulk discovery → feeds `stage_leads` bar | read-only (external) |
| *(phase 2a — note)* | | Gmail draft creation is a **side effect of operator Approve**, not an agent tool — the agent never touches Gmail | |

*Operator-only actions (waitlist reorder, promotion, payment recording, fulfillment checklist, approve, mark-sent, archive) are REST/UI, deliberately not agent tools — they are the owner-control surface.*

**Resources** — single-sourced from `guidance/` + settings; duplicated into tool responses where the agent must not miss them:

- `postcard://reference/workflow` — the state machines, **step-by-step playbook** (orient → stage → claim → research → attach → draft → read comments → revise → waitlist when blocked), and which tool effects which transition; written so an agent with zero prior context can work the pipeline
- `postcard://reference/quality-bars` — staging bar, research bar (premise vs. hooks defined with examples), the disqualification vocabulary with when-to-use guidance, and the active-is-protected guards
- `postcard://reference/email-expectations` — what a good outreach email looks like: structure (lead with the hook, one ask, scarcity framing "one {category} per card"), the operator's `outreach_instructions` verbatim, and price discipline (from settings — never invented)
- `postcard://reference/sender` — the operator's business profile and personal notes, for tailoring emails and for the operator's own card slot
- `postcard://reference/slot-spec` — slot JSON schema + constraints + 3 exemplar slots
- `postcard://reference/template` — description of the active layout template(s) (grid, dimensions, margins)
- `postcard://reference/pricing` — pricing sheet generated from settings

**Plugin skills** are generated from the same `guidance/` sources at build time: `outreach/SKILL.md` (workflow + quality bars + email expectations + session ritual: always orient via `postcard_get_campaign_status` first; hard rules: never imply an email was sent, never research a disqualified lead, recommend waitlist when exclusivity blocks) and `postcard-design/SKILL.md` (slot constraints, legibility rules — contrast ≥ 4.5:1, one focal element, ≤2 type sizes per slot — plus exemplar and anti-example slots).

**REST mirror:** `/api/settings`, `/api/businesses` (incl. nested contacts, marks `operator_viewed_at` on detail fetch), `/api/campaigns/{id}/board` (slots + waitlists + summary roll-ups), `/api/participations/{id}` (status, payment, fulfillment patches), `/api/participations/{id}/promote`, `/api/campaigns/{id}/waitlist-order`, `/api/emails/{id}` (operator edit → next version), `/api/emails/{id}/approve`, `/api/emails/{id}/mark-sent`, `/api/comments`, `/api/activity`, `/api/postcards/{campaign_id}/render` — each dashboard screen hydrates from one composite endpoint.

## 5. Postcard model & rendering

**Templates** (in-repo, versioned, identified by `template_id`): phase 1 ships exactly one — `grid-4x2-v1`: postcard at 6×4 in nominal, 4×2 slot grid, fixed margins and gutter, header strip ("Lafayette Local Business Spotlight — June"). The agent never writes template HTML. Alternate sectionings (premium 3-slot, 6-slot, agent-chosen layouts) are future templates: slot content stays structured, drafts already record their `template_id`, so layout flexibility is additive.

**Slot object:**

```json
{
  "slot": 3,
  "business_id": "…",
  "headline": "string ≤ 6 words",
  "offer_text": "string ≤ 12 words",
  "contact_line": "phone or URL, one line",
  "logo_url": "https… (operator-provided or omitted)",
  "accent_color": "#hex",
  "offer_html": "optional constrained fragment, rendered ONLY inside the offer area"
}
```

**Rendering pipeline:** slots JSON → server-side Jinja render of the targeted template → server-side sanitize of `offer_html` (`nh3`: allowlist of `b/i/em/strong/br/span` + `style` limited to color/font-size) → dashboard displays inside `<iframe sandbox="">` (no scripts, no top navigation) → DOMPurify pass client-side as belt-and-braces. Empty slots render as labeled placeholders.

**Future, explicitly out of scope now:** (a) print renderer — second consumer of the same slot JSON, HTML→PDF at 300dpi with bleed; (b) artwork generation — button-triggered step where the agent hands the approved structured draft to an image model for high-quality final art. Both are enabled by, and require nothing beyond, the structured slot model.

## 6. Testing

| Seam | Harness | Representative assertions |
|---|---|---|
| **Service (primary)** | pytest + Postgres in Docker | staging without website rejected w/ bar restated; dedupe names existing record; double-claim fails; stale claim reclaimable; research without contact/premise/hook/evidence rejected; contact CRUD (upsert corrects, delete removes, one primary enforced, **last-contact delete blocked on active advertiser**); DQ requires valid code, `other` requires note, **DQ blocked on active participation**; draft save → version N+1 `in_review` w/ author, prior in-review `superseded`; operator edit creates operator-attributed version; approve only from `in_review`; second `committed` in category rejected **with waitlist recommendation** (service *and* index); waitlist append keeps dense order; reorder persists; **promotion blocked while slot occupied, succeeds after decline, requires amount**; payment fields recordable only at committed+; fulfillment editable only at committed+; `asking_price` snapshot survives settings change; remove-from-campaign blocked past `contacted`; campaign archive is reversible-only-by-operator |
| **MCP contract** | FastMCP in-process client | schema validation errors actionable; read-only tools mutate nothing; `get_campaign_status` includes settings, sender, instructions, and ordered waitlists; every call logged to `agent_activity`; tool list matches §4 |
| **HTTP** | FastAPI TestClient | composite endpoints return documented JSON shapes incl. summary roll-ups; business detail fetch sets `operator_viewed_at`; promote/waitlist-order/payment/fulfillment patches enforce the same service rules |
| **Render** | snapshot + sanitize tests | slots JSON → stable HTML snapshot per template_id; `<script>`/`onerror` payloads in `offer_html` stripped; iframe attrs present |
| **Agent eval** | mcp-builder style, 10 read-only Q&As | run manually against seeded data before Grant's first session |

UI: manual, using the PRD's UI Requirements section as the checklist.

## 7. Email delivery design (the Gmail decision)

Adopts the founder principle — the system never sends — and makes it structural:

- **Phase 1 (no Gmail at all):** Approve → **Copy** button → operator sends from own inbox → **Mark Sent**. The approved version is canonical.
- **Phase 2a (Gmail drafts):** operator Approve additionally calls the Gmail API to create a draft of the approved version, storing `gmail_draft_id`. OAuth scope is **limited to draft creation — the application never holds send permission**, so "never sends automatically" is enforced by credentials, not policy. **One-way push, no sync-back:** post-approval edits made inside Gmail are the operator's prerogative and are not mirrored; Gmail is an off-ramp, not a second editor. Mark Sent remains a manual click.
- **Phase 2b (chains):** inbox ingestion adds `direction`/`external_message_id`/`in_reply_to` to `emails`; replies join the participation's thread, advance outreach status, and capture committed amounts; sent-detection can then retire the manual Mark Sent.
- A much later opt-in send-on-approve mode is possible but deliberately unplanned.

## 8. Deployment & phases

**Phase 1:** `docker-compose up` — `postgres:16` + server image (serves `/api`, `/mcp`, and the built SPA as static files). Runs on localhost or one small private EC2 box (no public exposure required; if on EC2, security-group restrict to your IPs — auth itself is phase 2). Nightly `pg_dump` to a mounted volume.

**Phase 2:** 2a — Gmail draft creation on Approve (drafts-only OAuth scope); basic login; optional `postcard_discover_businesses` Places tool. 2b — inbox ingestion turning emails into chains with per-message thread UI; outreach analytics view; print/mailing-list export (provider-agnostic: import lists, export for USPS/mail houses, no tight integration); postcard artwork generation; tasks module; global search; fuzzy dedupe with approval queue.

**Phase 3:** conversational gateway — small Discord bot / Twilio webhook on the same box embedding the Agent SDK with this plugin; it is *just another MCP client*, no server changes. Scheduled background runs land in the existing `agent_activity` feed.

**Later:** hosted background agent (calls the same service layer), campaign-success analytics and pricing recommendations (founder philosophy: consistent fast sell-outs should raise prices), multi-tenant SaaS, advertiser portal. Nothing in phase 1 is throwaway; every later phase is an additional client of the same services.



