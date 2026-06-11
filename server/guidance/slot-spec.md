# Postcard slot spec

A postcard draft is an array of slot objects inside a frozen, versioned template. You write
slot content; you never write template HTML. Alternate layouts are new templates, not
freeform changes.

## Slot object

```json
{
  "slot": 3,
  "business_id": "uuid of the committed business (optional but expected)",
  "headline": "string, ≤ 6 words",
  "offer_text": "string, ≤ 12 words",
  "contact_line": "phone or URL, one line",
  "logo_url": "https url, operator-provided, or omit",
  "accent_color": "#hex",
  "offer_html": "optional constrained fragment, rendered ONLY inside the offer area"
}
```

Constraints (enforced on save):

- `slot` is an integer 1..total_slots, unique within the draft
- `headline` required, ≤ 6 words; `offer_text` ≤ 12 words; `contact_line` single line
- `accent_color` hex like `#1a6b3c`; `logo_url` http(s)
- `offer_html` may use only `b i em strong br span`, with `style` limited to color and
  font-size — everything else is stripped by the sanitizer

## Legibility rules

- One focal element per slot — the offer **or** the headline carries the weight, not both.
- ≤ 2 type sizes per slot; contrast ≥ 4.5:1 against the slot background.
- Empty slots render as labeled placeholders — never collapse or pad them with filler.

## Exemplar slots

```json
{"slot": 1, "headline": "Roof storm check, free", "offer_text": "Free 20-point roof inspection this month", "contact_line": "(765) 555-0142 · summitroofing.com", "accent_color": "#8a2f1d"}
```

```json
{"slot": 4, "headline": "Lafayette's 4.9★ plumber", "offer_text": "$40 off any water heater install", "contact_line": "rapidsplumbing.com", "accent_color": "#1d4e8a", "offer_html": "<b>$40 off</b> any <span style=\"color:#1d4e8a\">water heater</span> install"}
```

Anti-example — rejected or illegible:

```json
{"slot": 2, "headline": "The best home services company in the greater Lafayette area", "offer_text": "We do roofing, siding, gutters, windows, doors, decks and more, call now for a great deal"}
```

(headline 10 words; offer 17 words; no focal element; no contact line.)
