"""Shared user dependency.

X-User-Email is accepted only in development/test. Production requests must
present a signed, unexpired bearer token issued by /api/auth.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..auth_service import verify_access_token
from ..config import get_settings
from ..db import get_db
from ..models import User
from ..services import character_service


def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    environment = settings.environment.strip().lower()
    if authorization and authorization.lower().startswith("bearer "):
        user_id = verify_access_token(authorization[7:].strip(), settings.auth_secret_key)
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="Account not found")
        return user

    if environment in {"prod", "production"}:
        raise HTTPException(status_code=401, detail="Sign in to access this resource")

    email = (x_user_email or "demo@saathi.app").strip().lower()
    if "@" not in email or len(email) > 254:
        raise HTTPException(status_code=400, detail="Invalid user email")
    return character_service.get_or_create_user(db, email)
