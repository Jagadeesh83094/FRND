"""Conversation history routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CharacterConversation, User
from ..schemas import ConversationOut, MessageOut
from ..services import conversation_service
from .deps import get_current_user

router = APIRouter(prefix="/api", tags=["conversations"])


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return conversation_service.list_conversations(db, user)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(
    conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    convo = db.get(CharacterConversation, conversation_id)
    if convo is None or convo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_service.messages_for_conversation(db, convo)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    convo = db.get(CharacterConversation, conversation_id)
    if convo is None or convo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(convo)
    db.commit()
    return {"deleted": conversation_id}
