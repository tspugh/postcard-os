# postcard plugin

Claude plugin for the postcard-os MCP server.

- `.mcp.json` points at the local server (`http://localhost:8000/mcp/`) — start the stack
  with `docker compose up` first.
- `skills/` are **generated** from `server/guidance/` by `make build-skills`. Edit the
  guidance, not the skills; the same markdown is served live as MCP resources.

Install for local use:

```sh
claude plugin install /srv/ssd/Projects/postcard-os/plugin
```
