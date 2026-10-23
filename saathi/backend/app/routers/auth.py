"""Account registration and login endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth_service import hash_password, issue_access_token, verify_password
from ..config import get_settings
from ..db import get_db
from ..models import AuthCredential, User
from ..rate_limit import enforce_rate_limit
from ..schemas import AuthIn, AuthOut

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _response(user: User, credential: AuthCredential) -> AuthOut:
    settings = get_settings()
    token = issue_access_token(user.id, settings.effective_auth_secret_key)
    return AuthOut(access_token=token, token_type="bearer", expires_in=43200,
                   user_id=user.id, email=user.email, display_name=user.display_name)


@router.post("/register", response_model=AuthOut, status_code=201)
def register(payload: AuthIn, request: Request, db: Session = Depends(get_db)):

    enforce_rate_limit(request, bucket="auth-register", limit=5)
    email = payload.email.strip().lower()
    if len(email) > 254 or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if len(payload.password) < 12:
        raise HTTPException(status_code=422, detail="Password must contain at least 12 characters")
    if len(payload.password) > 256:
        raise HTTPException(status_code=422, detail="Password is too long")
    if db.scalar(select(User).where(UserModel.email == email)) is not None:
        raise HTTPException(status_code=409, detail="Unable to create account with those details")
    user = UserModel(email=email, display_name=(payload.display_name or email.split("@")[0])[:120])
    db.add(user)
    db.flush()
    credential = AuthCredential(user_id=user.id, password_hash=hash_password(payload.password))
    db.add(credential)
    db.commit()
    db.refresh(user)
    db.refresh(credential)
    return _response(user, credential)


@router.post("/login", response_model=AuthOut)
def login(payload: AuthIn, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(request, bucket="auth-login", limit=10)
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == user.id)) if user else None
    if credential is None or not verify_password(payload.password, credential.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return _response(user, credential)
