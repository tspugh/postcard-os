from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.db import get_session
from server.services.settings import get_settings, settings_to_dict, update_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def read_settings(session: Session = Depends(get_session)):
    return settings_to_dict(get_settings(session))


@router.patch("")
def patch_settings(fields: dict, session: Session = Depends(get_session)):
    return settings_to_dict(update_settings(session, fields))
