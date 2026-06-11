# postcard-os

Local Business Postcard Campaign Platform — a single-operator web app plus an MCP server that
lets a Claude agent work a lead pipeline (stage → research → draft → commit/waitlist) while the
human approves everything that leaves the building.

Specs: [docs/PRD.md](docs/PRD.md) · [docs/TRD.md](docs/TRD.md). The docs are the source of truth.

## Layout

```
server/          FastAPI app (one process)
  api/           REST routes — dashboard contract (thin)
  mcp/           FastMCP server mounted at /mcp — agent contract (thin)
  services/      ALL business rules live here; both contracts delegate
  guidance/      single-source markdown → MCP resources AND plugin skills
  templates/     postcard layout templates (Jinja, versioned by template_id)
  models/        SQLAlchemy models
  migrations/    Alembic
plugin/          Claude plugin (manifest + skills generated from guidance/)
web/             React SPA (phase-1 UI; not built yet)
docs/            PRD + TRD
```

## Run

```sh
docker compose up --build     # postgres:16 + server on http://localhost:8000
```

- REST: `http://localhost:8000/api/...`
- MCP (Streamable HTTP): `http://localhost:8000/mcp/`
- No auth in phase 1 — bind to localhost or a firewalled box only.

## Develop

```sh
uv sync                       # python 3.12 env
docker compose up postgres -d
make migrate
make dev                      # uvicorn --reload on :8000
```

## Test

```sh
make test                     # spins a throwaway postgres:16 on :5433, runs pytest
```

Tests target the service layer against real Postgres (the state machines are tested once,
beneath both REST and MCP), plus MCP-contract, HTTP-contract, and render/sanitize seams.
