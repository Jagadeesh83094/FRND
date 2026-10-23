"""Conversation storage and history assembly."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import CharacterConversation, Message, User, UserCharacter


def get_or_create_active_conversation(
    db: Session, user: User, uc: UserCharacter
) -> CharacterConversation:
    convo = db.scalar(
        select(CharacterConversation).where(
            CharacterConversation.user_id == user.id,
            CharacterConversation.user_character_id == uc.id,
            CharacterConversation.is_active.is_(True),
        ).order_by(CharacterConversation.id.desc())
    )
    if convo:
        return convo
    convo = CharacterConversation(
        user_id=user.id,
        user_character_id=uc.id,
        title=f"Chat with {uc.display_name}",
    )
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


def add_message(
    db: Session,
    convo: CharacterConversation,
    *,
    role: str,
    content: str,
    language: str | None = None,
    audio_ref: str | None = None,
    meta: dict | None = None,
) -> Message:
    msg = Message(
        conversation_id=convo.id,
        role=role,
        content=content,
        language=language,
        audio_ref=audio_ref,
        meta=meta or {},
    )
    db.add(msg)
    convo.last_message_at = func.now()
    db.commit()
    db.refresh(msg)
    return msg


def history_for_prompt(
    db: Session, convo: CharacterConversation, limit_turns: int = 16
) -> list[dict]:
    """Return the last N turns as {role, content} for the chat provider."""
    msgs = list(db.scalars(
        select(Message).where(Message.conversation_id == convo.id)
        .order_by(Message.id.desc()).limit(limit_turns * 2)
    ))
    msgs.reverse()
    return [{"role": m.role, "content": m.content} for m in msgs if m.role in ("user", "assistant")]


def list_conversations(db: Session, user: User) -> list[dict]:
    rows = list(db.scalars(
        select(CharacterConversation).where(CharacterConversation.user_id == user.id)
        .order_by(CharacterConversation.last_message_at.desc().nullslast(), CharacterConversation.id.desc())
    ))
    out = []
    for c in rows:
        uc = db.get(UserCharacter, c.user_character_id)
        count = db.scalar(
            select(func.count()).select_from(Message).where(Message.conversation_id == c.id)
        ) or 0
        out.append({
            "id": c.id,
            "user_character_id": c.user_character_id,
            "character_name": uc.display_name if uc else "Unknown",
            "title": c.title,
            "last_message_at": c.last_message_at,
            "message_count": count,
        })
    return out


def messages_for_conversation(db: Session, convo: CharacterConversation) -> list[Message]:
    return list(db.scalars(
        select(Message).where(Message.conversation_id == convo.id).order_by(Message.id)
    ))
