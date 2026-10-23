"""Memory and sharing-permission routes (requirement F controls)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CharacterDefinition, Memory, User, UserCharacter
from ..schemas import MemoryCreate, MemoryGrant, MemoryOut
from ..services import character_service, memory_service
from .deps import get_current_user

router = APIRouter(prefix="/api", tags=["memories"])


@router.get("/memories", response_model=list[MemoryOut])
def list_memories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [memory_service.memory_to_out(db, m) for m in memory_service.list_memories(db, user)]


@router.post("/memories", response_model=MemoryOut, status_code=201)
def create_memory(
    payload: MemoryCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    # A memory created here is a shared/global fact; per-character memories use
    # POST /memories/for-character/{character_id}.
    origin: UserCharacter | None = None
    mem = memory_service.create_memory(
        db, user=user, origin=origin, content=payload.content,
        category=payload.category, sensitivity=payload.sensitivity,
        share_with=payload.share_with,
    )
    return memory_service.memory_to_out(db, mem)


@router.post("/memories/for-character/{character_id}", response_model=MemoryOut, status_code=201)
def create_memory_for_character(
    character_id: str,
    payload: MemoryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    definition = db.get(CharacterDefinition, character_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Character not found")
    uc = character_service.get_or_create_user_character(db, user, character_id)
    mem = memory_service.create_memory(
        db, user=user, origin=uc, content=payload.content,
        category=payload.category, sensitivity=payload.sensitivity,
        share_with=payload.share_with,
    )
    return memory_service.memory_to_out(db, mem)


def _owned_memory(db: Session, user: User, memory_id: int) -> Memory:
    mem = db.get(Memory, memory_id)
    if mem is None or mem.user_id != user.id:
        raise HTTPException(status_code=404, detail="Memory not found")
    return mem


@router.post("/memories/grant", response_model=MemoryOut)
def grant(
    payload: MemoryGrant, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    mem = _owned_memory(db, user, payload.memory_id)
    target = db.get(UserCharacter, payload.user_character_id)
    if target is None or target.user_id != user.id:
        raise HTTPException(status_code=404, detail="Character not found")
    memory_service.grant_memory(db, user, mem, target)
    return memory_service.memory_to_out(db, mem)


@router.post("/memories/revoke", response_model=MemoryOut)
def revoke(
    payload: MemoryGrant, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    mem = _owned_memory(db, user, payload.memory_id)
    target = db.get(UserCharacter, payload.user_character_id)
    if target is None or target.user_id != user.id:
        raise HTTPException(status_code=404, detail="Character not found")
    memory_service.revoke_memory(db, user, mem, target)
    return memory_service.memory_to_out(db, mem)


@router.delete("/memories/{memory_id}")
def delete_memory(
    memory_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    mem = _owned_memory(db, user, memory_id)
    db.delete(mem)
    db.commit()
    return {"deleted": memory_id}


@router.delete("/user/data")
def delete_all_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete all user data (characters, conversations, messages, memories)."""
    return memory_service.delete_all_user_data(db, user)
