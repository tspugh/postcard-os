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
