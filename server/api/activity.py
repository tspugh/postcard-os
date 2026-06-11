from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.db import get_session
from server.services.activity import list_activity

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("")
def feed(limit: int = 50, session: Session = Depends(get_session)):
    """Agent activity feed — every MCP tool call, newest first. 'Did the agent run?'
    is answerable from the home screen."""
    return list_activity(session, limit=limit)
