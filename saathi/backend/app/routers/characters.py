"""Character library, customisation and voice catalog routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CharacterConversation, CharacterDefinition, User, UserCharacter
from ..safety import CustomCharacterError
from ..schemas import (
    CharacterOut,
    CustomCharacterCreate,
    UserCharacterUpdate,
    VoiceCatalogEntry,
)
from ..services import character_service, memory_service
from ..voice_catalog import V4_VOICES
from .deps import get_current_user

router = APIRouter(prefix="/api", tags=["characters"])


def _resolve(db: Session, user: User, character_id: str) -> tuple[CharacterDefinition, UserCharacter]:
    definition = db.get(CharacterDefinition, character_id)
    if definition is None or not definition.is_active:
        raise HTTPException(status_code=404, detail="Character not found")
    uc = character_service.get_or_create_user_character(db, user, character_id)
    return definition, uc


@router.get("/characters", response_model=list[CharacterOut])
def list_characters(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return character_service.list_user_characters(db, user)


@router.get("/voices", response_model=list[VoiceCatalogEntry])
def list_voices():
    """The curated v4-flash persona catalog (real, confirmed IDs)."""
    return [
        {"id": vid, "speaker": info["speaker"], "language": info["language"], "style": info["style"]}
        for vid, info in V4_VOICES.items()
    ]


@router.post("/characters/custom", response_model=CharacterOut, status_code=201)
def create_custom(
    payload: CustomCharacterCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return character_service.create_custom_character(db, user, payload.model_dump())
    except CustomCharacterError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/characters/{character_id}", response_model=CharacterOut)
def get_character(character_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    definition, uc = _resolve(db, user, character_id)
    return character_service.character_to_dict(db, definition, uc)


@router.post("/characters/{character_id}/new-chat")
def create_new_chat(
    character_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a separate conversation while preserving older conversations."""
    from ..services import conversation_service

    _definition, uc = _resolve(db, user, character_id)
    db.query(CharacterConversation).filter(
        CharacterConversation.user_id == user.id,
        CharacterConversation.user_character_id == uc.id,
        CharacterConversation.is_active.is_(True),
    ).update({CharacterConversation.is_active: False}, synchronize_session=False)
    db.commit()

    convo = conversation_service.get_or_create_active_conversation(db, user, uc)
    return {"conversation_id": convo.id, "messages": []}


@router.get("/characters/{character_id}/session")
def character_session(character_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Everything needed to open a character cleanly (used on character switch)."""
    from ..services import conversation_service

    definition, uc = _resolve(db, user, character_id)
    character = character_service.character_to_dict(db, definition, uc)
    convo = conversation_service.get_or_create_active_conversation(db, user, uc)
    messages = conversation_service.messages_for_conversation(db, convo)
    mems = memory_service.accessible_memories(db, uc)
    return {
        "character": character,
        "conversation_id": convo.id,
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content, "language": m.language,
             "created_at": m.created_at, "meta": m.meta or {}}
            for m in messages
        ],
        "memory_count": len(mems),
        "memories": [memory_service.memory_to_out(db, m) for m in mems],
    }


@router.patch("/characters/{character_id}", response_model=CharacterOut)
def update_character(
    character_id: str,
    payload: UserCharacterUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    definition, uc = _resolve(db, user, character_id)
    try:
        uc = character_service.update_user_character(db, user, uc, payload.model_dump(exclude_none=True))
    except CustomCharacterError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return character_service.character_to_dict(db, definition, uc)


@router.delete("/characters/{character_id}/history")
def delete_character_history(
    character_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _definition, uc = _resolve(db, user, character_id)
    return memory_service.delete_character_history(db, user, uc)
