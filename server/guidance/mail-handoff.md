# Mail handoff — placing approved emails into the operator's drafts

Approved ≠ sent. Once the operator approves a version in the dashboard, your job is to
carry it into the operator's **own mailbox as a draft**, so sending is one click in their
mail client. Gmail is the first supported provider; the flow is the same for any future
one. The postcard server never talks to the mailbox — you do, through the operator's
connected mail tool (e.g. a Gmail MCP connector with a create-draft capability).

## When

`postcard_get_campaign_status` returns `approved_awaiting_handoff` on the campaign board:
every approved version not yet handed off, with recipient (`to`), `subject`, and `body`.
Work this list during the session ritual, right after orienting.

## How

1. **Check for a connected mail tool.** If no Gmail (or other mail) connector is available
   in your session, skip the handoff entirely and tell the operator the dashboard's Copy
   button flow still works. Never improvise delivery and never treat a missing connector
   as something to work around.
2. **Create the draft** in the operator's mailbox:
   - **To:** the `to` address from the record — the business's contact on record. If `to`
     is null, there is no usable email contact: skip it and flag it as research work.
     Never guess an address.
   - **Subject and body: verbatim.** The approved version is canonical — never rephrase,
     trim, sign differently, or "improve" it on the way to the mailbox.
3. **Link it back:** `postcard_link_mail_draft(email_id, provider_draft_id)` with the
   draft id the provider returned. The dashboard then shows the version as in the
   operator's drafts. Retrying with the same draft id is safe; the tool rejects a second,
   different draft for the same email.

## Hard rules

- **Drafts only, ever.** You never send, schedule, reply, or touch any other message in
  the operator's mailbox. If a mail tool offers a send capability, it is not yours to use.
- **Only approved versions** are handed off — the tool enforces it. In-review work stays
  in the dashboard.
- **One approved email, one mailbox draft.** If you accidentally created a duplicate
  draft, delete the duplicate you just made and keep the linked one.
- Post-handoff edits the operator makes inside their mailbox are their prerogative — the
  handoff is one-way, with no sync-back.
- Sending and **Mark Sent** remain the operator's hands: their mail client, their
  dashboard click.
