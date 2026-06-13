# postcard plugin

Claude plugin for the postcard-os MCP server.

- `.mcp.json` points at the local server (`http://localhost:8000/mcp/`) — start the stack
  with `docker compose up` first.
- `skills/` are **generated** from `server/guidance/` by `make build-skills`. Edit the
  guidance, not the skills; the same markdown is served live as MCP resources.

## Gmail handoff (optional)

The campaign-outreach skill hands **operator-approved** emails into the operator's Gmail
as drafts. That requires a Gmail MCP connector in the same Claude Code session — e.g. the
claude.ai Gmail connector (`/mcp` → connect Gmail) or any Gmail MCP server exposing a
create-draft tool — authenticated as the mailbox the operator sends from (a dedicated
outreach account works well). The plugin deliberately does not bundle Gmail credentials;
the connector and its auth belong to the operator. With no mail connector in the session,
the skill skips handoff and the dashboard's Copy → Mark Sent flow is unchanged. The agent
only ever creates drafts of approved versions — it has no send capability anywhere in
this surface, and the linkage is recorded via `postcard_link_mail_draft`.

Install for local use:

```sh
claude plugin install /srv/ssd/Projects/postcard-os/plugin
```
