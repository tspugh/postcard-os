from sqlalchemy import select
from sqlalchemy.orm import Session

from server.models import AgentActivity
from server.services.serialize import activity_to_dict

MAX_ARG_CHARS = 300


def summarize_args(args: dict | None) -> dict | None:
    """Redacted/truncated digest — the feed needs 'what happened', not payload dumps."""
    if not args:
        return None
    out = {}
    for key, value in args.items():
        text = value if isinstance(value, (str, int, float, bool)) or value is None else repr(value)
        text = str(text)
        out[key] = text[:MAX_ARG_CHARS] + ("…" if len(text) > MAX_ARG_CHARS else "")
    return out


def log_activity(session: Session, tool_name: str, args: dict | None, outcome: str, detail: str | None = None) -> None:
    session.add(
        AgentActivity(
            tool_name=tool_name,
            args_summary=summarize_args(args),
            outcome=outcome,
            detail=detail,
        )
    )
    session.flush()


def list_activity(session: Session, limit: int = 50) -> list[dict]:
    rows = session.scalars(select(AgentActivity).order_by(AgentActivity.created_at.desc()).limit(limit))
    return [activity_to_dict(a) for a in rows]
