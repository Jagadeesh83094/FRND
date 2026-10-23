"""Chat turn + greeting routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CharacterDefinition, User
from ..providers import ProviderError
from ..rate_limit import enforce_rate_limit
from ..schemas import ChatTurnIn, ChatTurnOut
from ..services import character_service, chat_service
from .deps import get_current_user

router = APIRouter(prefix="/api", tags=["chat"])


def _resolve(db: Session, user: User, character_id: str) -> tuple[CharacterDefinition, object]:
    definition = db.get(CharacterDefinition, character_id)
    if definition is None or not definition.is_active:
        raise HTTPException(status_code=404, detail="Character not found")
    uc = character_service.get_or_create_user_character(db, user, character_id)
    return definition, uc


def _provider_error(exc: ProviderError) -> HTTPException:
    status = 503 if exc.kind in ("rate_limit", "timeout", "server", "network") else 502
    if exc.kind in ("credits", "credits_exhausted"):
        status = 402
    return HTTPException(status_code=status, detail={"kind": exc.kind, "message": exc.user_message()})


@router.post("/characters/{character_id}/chat", response_model=ChatTurnOut)
async def chat_turn(
    character_id: str,
    payload: ChatTurnIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, bucket="chat", limit=30)
    _definition, uc = _resolve(db, user, character_id)
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail="Empty message")
    try:
        return await chat_service.run_turn(
            db, user, uc, payload.text.strip(),
            mode=payload.mode, language=payload.language, speak=payload.speak,
        )
    except ProviderError as exc:
        raise _provider_error(exc)


@router.post("/characters/{character_id}/greeting", response_model=ChatTurnOut)
async def greeting(
    character_id: str,
    request: Request,
    speak: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, bucket="greeting", limit=20)
    _definition, uc = _resolve(db, user, character_id)
    try:
        return await chat_service.greeting(db, user, uc, speak=speak)
    except ProviderError as exc:
        raise _provider_error(exc)
