"""Shared router dependencies.

The email-header identity is ONLY a local-development convenience. It is not
authentication. Production must not silently accept caller-controlled identity.
Replace this adapter with a verified session/JWT identity provider before
enabling public user routes.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import User
from ..services import character_service


def get_current_user(
    x_user_email: str = Header(default="demo@saathi.app"),
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    if settings.environment.strip().lower() in {"prod", "production"}:
        raise HTTPException(
            status_code=503,
            detail=(
                "User authentication is not configured. The development "
                "X-User-Email identity adapter is disabled in production."
            ),
        )

    if "@" not in x_user_email or len(x_user_email) > 254:
        raise HTTPException(status_code=400, detail="Invalid user email")
    return character_service.get_or_create_user(db, x_user_email.strip().lower())
