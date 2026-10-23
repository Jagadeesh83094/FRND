"""Memory architecture and sharing permissions (requirement F).

Two kinds of context:
  1. Character-specific  -- a memory whose origin is that character.
  2. Shared, user-approved -- a memory explicitly granted to another character
     via conversation_memory_permissions.

Intimate conversation details are NEVER shared automatically.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    CharacterConversation,
    ConversationMemoryPermission,
    Memory,
    User,
    UserCharacter,
)


def create_memory(
    db: Session,
    *,
    user: User,
    origin: UserCharacter | None,
    content: str,
    category: str = "general",
    sensitivity: str = "normal",
    share_with: list[int] | None = None,
) -> Memory:
    mem = Memory(
        user_id=user.id,
        user_character_id=origin.id if origin else None,
        content=content.strip(),
        category=category,
        sensitivity=sensitivity,
    )
    db.add(mem)
    db.flush()
    for target_id in share_with or []:
        target = db.get(UserCharacter, target_id)
        if target and target.user_id == user.id and (origin is None or target.id != origin.id):
            _grant(db, user, mem, target)
    db.commit()
    db.refresh(mem)
    return mem


def _grant(db: Session, user: User, memory: Memory, target: UserCharacter) -> None:
    exists = db.scalar(
        select(ConversationMemoryPermission).where(
            ConversationMemoryPermission.memory_id == memory.id,
            ConversationMemoryPermission.granted_to_user_character_id == target.id,
        )
    )
    if exists:
        return
    db.add(ConversationMemoryPermission(
        memory_id=memory.id,
        granted_to_user_character_id=target.id,
        granted_by_user_id=user.id,
    ))
    db.flush()


def grant_memory(db: Session, user: User, memory: Memory, target: UserCharacter) -> None:
    if memory.user_id != user.id or target.user_id != user.id:
        raise PermissionError("Not your memory or character")
    _grant(db, user, memory, target)
    db.commit()


def revoke_memory(db: Session, user: User, memory: Memory, target: UserCharacter) -> None:
    if memory.user_id != user.id:
        raise PermissionError("Not your memory")
    row = db.scalar(
        select(ConversationMemoryPermission).where(
            ConversationMemoryPermission.memory_id == memory.id,
            ConversationMemoryPermission.granted_to_user_character_id == target.id,
        )
    )
    if row:
        db.delete(row)
        db.commit()


def accessible_memories(db: Session, uc: UserCharacter) -> list[Memory]:
    """Memories a given character is allowed to use."""
    own = list(db.scalars(
        select(Memory).where(
            Memory.user_character_id == uc.id,
            Memory.is_deleted.is_(False),
        )
    ))
    granted_ids = list(db.scalars(
        select(ConversationMemoryPermission.memory_id).where(
            ConversationMemoryPermission.granted_to_user_character_id == uc.id
        )
    ))
    granted: list[Memory] = []
    if granted_ids:
        granted = list(db.scalars(
            select(Memory).where(
                Memory.id.in_(granted_ids),
                Memory.is_deleted.is_(False),
            )
        ))
    # de-duplicate, keep order
    seen: set[int] = set()
    out: list[Memory] = []
    for m in own + granted:
        if m.id not in seen:
            seen.add(m.id)
            out.append(m)
    return out


def memory_content_for_prompt(db: Session, uc: UserCharacter, limit: int = 12) -> list[str]:
    mems = accessible_memories(db, uc)[-limit:]
    return [m.content for m in mems]


def memory_to_out(db: Session, memory: Memory) -> dict:
    origin = db.get(UserCharacter, memory.user_character_id) if memory.user_character_id else None
    perms = list(db.scalars(
        select(ConversationMemoryPermission).where(
            ConversationMemoryPermission.memory_id == memory.id
        )
    ))
    shared_ids = [p.granted_to_user_character_id for p in perms]
    names: list[str] = []
    for sid in shared_ids:
        uc = db.get(UserCharacter, sid)
        if uc:
            names.append(uc.display_name)
    return {
        "id": memory.id,
        "content": memory.content,
        "category": memory.category,
        "sensitivity": memory.sensitivity,
        "origin_user_character_id": memory.user_character_id,
        "origin_character_name": origin.display_name if origin else None,
        "shared_with": shared_ids,
        "shared_with_names": names,
        "created_at": memory.created_at,
    }


def list_memories(db: Session, user: User) -> list[Memory]:
    return list(db.scalars(
        select(Memory).where(Memory.user_id == user.id, Memory.is_deleted.is_(False))
        .order_by(Memory.id)
    ))


# --------------------------------------------------------------------------- #
# Deletion (requirement F controls)
# --------------------------------------------------------------------------- #
def delete_character_history(db: Session, user: User, uc: UserCharacter) -> dict:
    convos = list(db.scalars(
        select(CharacterConversation).where(
            CharacterConversation.user_character_id == uc.id,
            CharacterConversation.user_id == user.id,
        )
    ))
    for c in convos:
        db.delete(c)  # cascades to messages
    mems = list(db.scalars(
        select(Memory).where(Memory.user_character_id == uc.id, Memory.user_id == user.id)
    ))
    for m in mems:
        db.delete(m)
    db.commit()
    return {"conversations_deleted": len(convos), "memories_deleted": len(mems)}


def delete_all_user_data(db: Session, user: User) -> dict:
    """Full wipe: characters, conversations, messages, memories, permissions."""
    ucs = list(db.scalars(select(UserCharacter).where(UserCharacter.user_id == user.id)))
    for uc in ucs:
        db.delete(uc)
    db.commit()
    return {"characters_deleted": len(ucs)}
