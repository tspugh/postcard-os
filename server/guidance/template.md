# Active layout templates

## grid-4x2-v1 (phase-1 default, the only template)

- Postcard at 6×4 in nominal (rendered 900×600 px), portrait-content landscape card.
- **4×2 slot grid** — 8 slots, fixed margins (18px) and gutter (12px).
- Header strip across the top: "{Market} Local Business Spotlight — {Month}".
- Each slot: optional logo (top), headline, offer area (text or sanitized `offer_html`),
  contact line, slot number watermark. Accent color paints the slot border.
- Empty slots render dashed with their category label and "this space available".

The template is frozen: agents supply slot JSON only. Future premium layouts (3-slot,
6-slot) ship as new `template_id`s; drafts record the template they target, so old drafts
keep rendering exactly as designed.
