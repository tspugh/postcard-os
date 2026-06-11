"""Every MCP tool invocation is logged to agent_activity — the dashboard feed reads it.
Logging uses its own session so rejected/failed calls are recorded too (TRD §1)."""

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from server.db import session_scope
from server.services.activity import log_activity


class ActivityLogMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name
        args = context.message.arguments or {}
        try:
            result = await call_next(context)
        except ToolError as e:
            self._log(tool_name, args, "rejected", str(e))
            raise
        except Exception as e:
            self._log(tool_name, args, "error", f"{type(e).__name__}: {e}")
            raise
        self._log(tool_name, args, "ok", None)
        return result

    @staticmethod
    def _log(tool_name: str, args: dict, outcome: str, detail: str | None):
        try:
            with session_scope() as session:
                log_activity(session, tool_name, args, outcome, detail)
        except Exception:
            # The feed is observability, not a gate — never fail a tool call over logging.
            pass
