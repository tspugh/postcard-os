"""One process, two contracts: REST under /api (dashboard), FastMCP under /mcp (agent).
Both are thin wrappers over server.services — no business logic lives here."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.api import api_router
from server.db import session_scope
from server.errors import DomainError
from server.mcp import build_mcp
from server.services.settings import get_settings

mcp = build_mcp()
mcp_app = mcp.http_app(path="/", stateless_http=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed the single settings row (defaults: $299, canonical 8 categories, Lafayette IN)
    with session_scope() as session:
        get_settings(session)
    async with mcp_app.lifespan(app):
        yield


app = FastAPI(title="postcard-os", lifespan=lifespan)
app.mount("/mcp", mcp_app)
app.include_router(api_router, prefix="/api")


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/healthz")
def healthz():
    return {"ok": True}


# Serve the built SPA when web/dist exists (docker image phase); 404s fall through to /api docs.
_spa = Path(__file__).resolve().parent.parent / "web" / "dist"
if _spa.is_dir():
    app.mount("/", StaticFiles(directory=str(_spa), html=True), name="spa")
