"""Shared router dependencies."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..services import character_service


def get_current_user(
    x_user_email: str = Header(default="demo@saathi.app"),
    db: Session = Depends(get_db),
) -> User:
    """Lightweight identity for local dev.

    A real deployment replaces this with proper auth; the rest of the app only
    ever sees a User row, so nothing else changes.
    """
    if "@" not in x_user_email:
        raise HTTPException(status_code=400, detail="Invalid user email")
    return character_service.get_or_create_user(db, x_user_email.lower())
