from fastmcp import FastMCP

from server.mcp.middleware import ActivityLogMiddleware
from server.mcp.resources import register_resources
from server.mcp.tools import register_tools


def build_mcp() -> FastMCP:
    mcp = FastMCP(
        name="postcard",
        instructions=(
            "Lead pipeline for a shared local-business postcard. You are the worker; the "
            "operator is the reviewer. Start every session with postcard_get_campaign_status. "
            "Read postcard://reference/workflow and postcard://reference/quality-bars before "
            "staging or researching. Nothing here sends email — drafts go to human review, "
            "and approved drafts are handed into the operator's own mailbox via their mail "
            "connector (postcard://reference/mail-handoff), never sent."
        ),
    )
    register_tools(mcp)
    register_resources(mcp)
    mcp.add_middleware(ActivityLogMiddleware())
    return mcp
