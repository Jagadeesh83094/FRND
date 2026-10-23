"""Normalised data model for the multi-character companion platform.

New entities (requirement I):
    character_definitions, user_characters, character_preferences,
    character_conversations, conversation_memory_permissions, voice_configurations

Reused entities: users, messages, memories.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


# --------------------------------------------------------------------------- #
# Reused: users
# --------------------------------------------------------------------------- #
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), default="Friend")
    locale: Mapped[str] = mapped_column(String(16), default="en-IN")
    # Transparency: recorded when the user acknowledges characters are AI.
    ai_disclosure_ack_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    characters: Mapped[list["UserCharacter"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["CharacterConversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    memories: Mapped[list["Memory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# --------------------------------------------------------------------------- #
# voice_configurations  (kept separate from the chat prompt - requirement E)
# --------------------------------------------------------------------------- #
class VoiceConfiguration(Base, TimestampMixin):
    __tablename__ = "voice_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), default="sarvam")
    model: Mapped[str] = mapped_column(String(64), default="bulbul:v4-flash")
    speaker_id: Mapped[str] = mapped_column(String(96))
    language_code: Mapped[str] = mapped_column(String(16), default="en-IN")
    pace: Mapped[float] = mapped_column(Float, default=1.0)
    fallback_speaker: Mapped[str | None] = mapped_column(String(96))
    config_version: Mapped[int] = mapped_column(Integer, default=1)
    # True when this config is a built-in definition default (shared, read-only
    # for users) vs a per-user override.
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("provider", "model", "speaker_id", "language_code", name="uq_voice_identity"),
    )


# --------------------------------------------------------------------------- #
# character_definitions  (built-in, updatable without destroying customisations)
# --------------------------------------------------------------------------- #
class CharacterDefinition(Base, TimestampMixin):
    __tablename__ = "character_definitions"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)  # stable slug
    kind: Mapped[str] = mapped_column(String(16), default="builtin")  # builtin | custom
    display_name: Mapped[str] = mapped_column(String(80))
    default_nickname: Mapped[str | None] = mapped_column(String(80))
    # Regional name options the user may pick from (e.g. Mom/Amma/Maa).
    name_variants: Mapped[dict] = mapped_column(JSON, default=dict)
    avatar_ref: Mapped[str] = mapped_column(String(80), default="default")
    short_description: Mapped[str] = mapped_column(String(240))
    personality_description: Mapped[str] = mapped_column(Text)
    conversational_style: Mapped[str] = mapped_column(Text)
    # Structured tone knobs consumed by the prompt builder.
    tone: Mapped[dict] = mapped_column(JSON, default=dict)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    example_greeting: Mapped[str] = mapped_column(Text)
    response_length: Mapped[str] = mapped_column(String(16), default="short")
    behaviors: Mapped[list] = mapped_column(JSON, default=list)
    do_list: Mapped[list] = mapped_column(JSON, default=list)
    dont_list: Mapped[list] = mapped_column(JSON, default=list)
    default_voice_config_id: Mapped[int | None] = mapped_column(
        ForeignKey("voice_configurations.id", ondelete="SET NULL")
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    default_voice: Mapped[VoiceConfiguration | None] = relationship(
        foreign_keys=[default_voice_config_id]
    )

    __table_args__ = (Index("ix_character_definitions_kind", "kind"),)


# --------------------------------------------------------------------------- #
# user_characters  (a user's instance of a character + customisations)
# --------------------------------------------------------------------------- #
class UserCharacter(Base, TimestampMixin):
    __tablename__ = "user_characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Null only for fully custom characters with no template.
    character_definition_id: Mapped[str | None] = mapped_column(
        ForeignKey("character_definitions.id", ondelete="SET NULL")
    )
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    display_name: Mapped[str] = mapped_column(String(80))
    nickname: Mapped[str | None] = mapped_column(String(80))
    # User overrides of personality / style (validated - cannot touch safety).
    personality_overrides: Mapped[dict] = mapped_column(JSON, default=dict)
    language_prefs: Mapped[list] = mapped_column(JSON, default=list)
    response_length: Mapped[str] = mapped_column(String(16), default="short")
    voice_config_id: Mapped[int | None] = mapped_column(
        ForeignKey("voice_configurations.id", ondelete="SET NULL")
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="characters")
    definition: Mapped[CharacterDefinition | None] = relationship()
    voice_config: Mapped[VoiceConfiguration | None] = relationship(
        foreign_keys=[voice_config_id]
    )
    conversations: Mapped[list["CharacterConversation"]] = relationship(
        back_populates="user_character", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # One instance per built-in definition per user.
        UniqueConstraint("user_id", "character_definition_id", name="uq_user_character_definition"),
        Index("ix_user_characters_user", "user_id"),
    )


# --------------------------------------------------------------------------- #
# character_preferences  (flexible per-character settings)
# --------------------------------------------------------------------------- #
class CharacterPreference(Base, TimestampMixin):
    __tablename__ = "character_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_character_id: Mapped[int] = mapped_column(
        ForeignKey("user_characters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pref_key: Mapped[str] = mapped_column(String(64))
    pref_value: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("user_character_id", "pref_key", name="uq_character_pref_key"),
    )


# --------------------------------------------------------------------------- #
# character_conversations  (independent history per character - requirement F)
# --------------------------------------------------------------------------- #
class CharacterConversation(Base, TimestampMixin):
    __tablename__ = "character_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_character_id: Mapped[int] = mapped_column(
        ForeignKey("user_characters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="conversations")
    user_character: Mapped[UserCharacter] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id"
    )

    __table_args__ = (
        Index("ix_conversations_user_character", "user_id", "user_character_id"),
    )


# --------------------------------------------------------------------------- #
# Reused: messages
# --------------------------------------------------------------------------- #
class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("character_conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | system | tool
    content: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(16))
    # Reference to a transient audio blob id -- never the raw bytes.
    audio_ref: Mapped[str | None] = mapped_column(String(120))
    provider_message_id: Mapped[str | None] = mapped_column(String(120))
    tokens: Mapped[int | None] = mapped_column(Integer)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    conversation: Mapped[CharacterConversation] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_messages_conversation", "conversation_id"),)


# --------------------------------------------------------------------------- #
# Reused: memories  (user-owned facts; per-character by default)
# --------------------------------------------------------------------------- #
class Memory(Base, TimestampMixin):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Origin character. NULL == a global, user-authored memory.
    user_character_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_characters.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(48), default="general")
    # "normal" | "sensitive" | "intimate". Intimate never auto-shares.
    sensitivity: Mapped[str] = mapped_column(String(16), default="normal")
    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="memories")
    permissions: Mapped[list["ConversationMemoryPermission"]] = relationship(
        back_populates="memory", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_memories_user", "user_id"),)


# --------------------------------------------------------------------------- #
# conversation_memory_permissions  (explicit sharing grants - requirement F)
# --------------------------------------------------------------------------- #
class ConversationMemoryPermission(Base, TimestampMixin):
    __tablename__ = "conversation_memory_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    memory_id: Mapped[int] = mapped_column(
        ForeignKey("memories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # The character that is *granted* access to this memory.
    granted_to_user_character_id: Mapped[int] = mapped_column(
        ForeignKey("user_characters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    granted_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    memory: Mapped[Memory] = relationship(back_populates="permissions")

    __table_args__ = (
        UniqueConstraint("memory_id", "granted_to_user_character_id", name="uq_memory_grant"),
    )
