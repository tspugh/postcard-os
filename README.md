# postcard-os

`postcard-os` is a local, single-operator workspace for running shared local-business postcard campaigns. It combines a React dashboard, a FastAPI REST API, and an MCP server over one PostgreSQL-backed service. An MCP client can research and stage leads, draft outreach, and prepare postcard content while the operator retains control of approvals, sending, commitments, payments, and fulfillment.

The project is an early-stage reference implementation. It is designed for local development and evaluation, not unattended or internet-facing operation.

## What it supports

- A lead pipeline from staging and research through outreach, commitment, waitlisting, payment, and fulfillment
- Category exclusivity, campaign slot assignment, and ordered waitlists
- Versioned outreach drafts with comments and explicit operator approval
- Versioned postcard layouts rendered from structured slot content
- A React dashboard for leads, campaigns, activity, and settings
- REST and MCP contracts backed by the same service layer
- An optional Claude plugin whose guidance is generated from the server's canonical workflow documents

The application records workflow state; it does not send email or charge customers. A `sent` email state means the operator confirmed that they sent the message outside the application.

## Safety boundary

Phase 1 has no authentication or authorization layer. Docker Compose binds the web/API service and PostgreSQL to `127.0.0.1`, and the bundled MCP configurations point to `localhost`.

Keep the service on a trusted machine. Do not expose port `8000`, port `5434`, or the MCP endpoint to a public or untrusted network. Add authentication, transport security, secret management, and deployment-specific access controls before adapting it for a shared or hosted environment.

## Quick start

Requirements:

- Docker with Compose v2
- Ports `8000` and `5434` available on the local host

Start the complete stack:

```sh
docker compose up --build
```

The first start builds the React application, starts PostgreSQL 16, applies Alembic migrations, and starts the API after the database health check passes.

Open:

- Dashboard: <http://localhost:8000>
- Health check: <http://localhost:8000/healthz>
- REST API documentation: <http://localhost:8000/docs>
- MCP endpoint (Streamable HTTP): `http://localhost:8000/mcp/`

Data is stored in the `pgdata` Docker volume. The backup service writes a daily PostgreSQL dump to the ignored local `backups/` directory. To stop the stack, run:

```sh
docker compose down
```

### Try the REST API

This example stages a fictional business using the reserved `.example` domain:

```sh
curl -X POST http://localhost:8000/api/businesses/stage \
  -H 'content-type: application/json' \
  -d '{
    "leads": [{
      "name": "Northstar Plumbing",
      "category": "plumber",
      "website": "https://northstar-plumbing.example"
    }]
  }'
```

Create a campaign with ISO dates:

```sh
curl -X POST http://localhost:8000/api/campaigns \
  -H 'content-type: application/json' \
  -d '{
    "name": "Example Spring Campaign",
    "market": "Example City",
    "month": "2027-04-01",
    "deadline": "2027-03-15"
  }'
```

The design prototypes under `docs/design-docs/` use illustrative seed content and are not loaded into the application database.

## MCP client setup

The repository-level `.mcp.json` and `plugin/.mcp.json` both configure a server named `postcard` at the local endpoint:

```json
{
  "mcpServers": {
    "postcard": {
      "type": "http",
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

Start the application before connecting an MCP client. Tool calls and operator actions share the same database and business rules.

## Architecture

```text
React dashboard ── REST /api ──┐
                               ├── service layer ── SQLAlchemy ── PostgreSQL
MCP client ────── HTTP /mcp ───┘
                                      │
                                      ├── workflow guidance/resources
                                      └── versioned postcard templates
```

```text
server/api/        Thin REST routes used by the dashboard
server/mcp/        FastMCP tools, resources, and activity middleware
server/services/   Shared workflow rules and state transitions
server/models/     SQLAlchemy models
server/migrations/ Alembic migrations
server/guidance/   Canonical workflow and quality guidance
server/templates/  Versioned Jinja postcard templates
web/               React/Vite dashboard
plugin/            Claude plugin manifest and generated skills
tests/             Service, HTTP, MCP, and rendering checks
docs/              Product and technical design documents
```

## Development

Requirements for local development:

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 22 or a compatible current Node.js release
- Docker, for PostgreSQL and the integration test database

Install Python dependencies and start PostgreSQL:

```sh
uv sync
docker compose up postgres -d
uv run alembic upgrade head
uv run uvicorn server.app:app --reload
```

In another terminal, run the dashboard development server:

```sh
cd web
npm ci
npm run dev
```

Vite serves the dashboard at <http://localhost:5173> and proxies `/api` to the FastAPI process on port `8000`.

To regenerate the plugin skills from `server/guidance/`:

```sh
make build-skills
```

## Tests

The test suite uses a disposable PostgreSQL 16 container bound to `127.0.0.1:5433`:

```sh
make test
```

The tests cover service-layer state transitions, REST and MCP contracts, activity logging, error behavior, postcard validation, and HTML sanitization. The Docker daemon must be running and port `5433` must be free.

The dashboard production build can be checked separately:

```sh
cd web
npm ci
npm run build
```

## Project status

The current `main` branch implements the phase 1 local workflow described above. The product and technical documents include planned capabilities as well as implemented behavior, so treat roadmap sections as design context rather than a promise that every described integration exists.

See [the product requirements](docs/PRD.md) and [the technical design](docs/TRD.md) for the data model, state machines, and design decisions.

This repository currently has no open-source license grant.
