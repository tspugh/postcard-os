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
