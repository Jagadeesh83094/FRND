"""Onboarding / transparency routes."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..schemas import OnboardingIn, OnboardingOut
from ..services.character_service import AI_DISCLOSURE
from .deps import get_current_user

router = APIRouter(prefix="/api", tags=["onboarding"])


@router.get("/onboarding", response_model=OnboardingOut)
def get_onboarding(user: User = Depends(get_current_user)):
    return {
        "ai_disclosure": AI_DISCLOSURE,
        "onboarding_completed": user.onboarding_completed,
        "user_id": user.id,
    }


@router.post("/onboarding", response_model=OnboardingOut)
def complete_onboarding(
    payload: OnboardingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if payload.display_name:
        user.display_name = payload.display_name.strip()[:120]
    if payload.locale:
        user.locale = payload.locale
    if payload.acknowledged_ai:
        user.ai_disclosure_ack_at = datetime.now(timezone.utc)
        user.onboarding_completed = True
    db.commit()
    db.refresh(user)
    return {
        "ai_disclosure": AI_DISCLOSURE,
        "onboarding_completed": user.onboarding_completed,
        "user_id": user.id,
    }
