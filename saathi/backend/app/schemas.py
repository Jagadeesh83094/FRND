"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

ResponseLength = Literal["short", "medium", "long"]
Sensitivity = Literal["normal", "sensitive", "intimate"]


class AuthIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)
    display_name: Optional[str] = Field(default=None, max_length=120)


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    email: str
    display_name: str


# --- Characters ------------------------------------------------------------ #
class VoiceConfigOut(BaseModel):
    provider: str
    model: str
    speaker_id: str
    language_code: str
    pace: float
    fallback_speaker: Optional[str] = None
    config_version: int
    is_fallback: bool = False
    fallback_reason: Optional[str] = None


class CharacterOut(BaseModel):
    id: str                      # definition id (slug) or "custom:<n>"
    definition_id: Optional[str] = None
    user_character_id: Optional[int] = None
    is_custom: bool = False
    display_name: str
    nickname: Optional[str] = None
    name_variants: dict[str, list[str]] = Field(default_factory=dict)
    avatar_ref: str = "default"
    short_description: str = ""
    personality_description: str = ""
    conversational_style: str = ""
    languages: list[str] = Field(default_factory=list)
    language_prefs: list[str] = Field(default_factory=list)
    example_greeting: str = ""
    response_length: ResponseLength = "short"
    behaviors: list[str] = Field(default_factory=list)
    voice: Optional[VoiceConfigOut] = None
    customized: bool = False


class UserCharacterUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=40)
    nickname: Optional[str] = Field(default=None, max_length=40)
    language_prefs: Optional[list[str]] = None
    response_length: Optional[ResponseLength] = None
    personality_overrides: Optional[dict[str, Any]] = None
    voice_id: Optional[str] = None
    voice_language: Optional[str] = None


class CustomCharacterCreate(BaseModel):
    display_name: str
    nickname: Optional[str] = None
    personality: str = ""
    conversational_style: str = ""
    language: str = "en-IN"
    tone: dict[str, float] = Field(default_factory=dict)
    voice_id: Optional[str] = None
    response_length: ResponseLength = "short"


class VoiceCatalogEntry(BaseModel):
    id: str
    speaker: str
    language: str
    style: str


# --- Conversations & messages --------------------------------------------- #
class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    language: Optional[str] = None
    created_at: datetime
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    user_character_id: int
    character_name: str
    title: Optional[str] = None
    last_message_at: Optional[datetime] = None
    message_count: int = 0


# --- Chat / voice turn ----------------------------------------------------- #
class ChatTurnIn(BaseModel):
    text: str
    mode: Literal["text", "voice"] = "text"
    language: Optional[str] = None
    speak: bool = False            # synthesize the reply to audio


class CrisisInfo(BaseModel):
    flagged: bool
    resources: list[dict] = Field(default_factory=list)


class ChatTurnOut(BaseModel):
    reply: str
    message_id: int
    conversation_id: int
    character_id: str
    character_name: str
    language: Optional[str] = None
    crisis: CrisisInfo
    memories_used: list[str] = Field(default_factory=list)
    audio_base64: Optional[str] = None
    audio_mime: Optional[str] = None
    voice: Optional[VoiceConfigOut] = None
    provider: str = "mock"
    latency_ms: Optional[int] = None


class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = None


class TTSOut(BaseModel):
    audio_base64: str
    mime_type: str
    speaker_id: str
    model: str
    language_code: str
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    provider: str = "mock"
    latency_ms: Optional[int] = None


class STTOut(BaseModel):
    text: str
    language_code: Optional[str] = None
    mode: str = "transcribe"
    provider: str = "mock"
    latency_ms: Optional[int] = None


# --- Memory ---------------------------------------------------------------- #
class MemoryCreate(BaseModel):
    content: str
    category: str = "general"
    sensitivity: Sensitivity = "normal"
    share_with: list[int] = Field(default_factory=list)  # user_character ids


class MemoryOut(BaseModel):
    id: int
    content: str
    category: str
    sensitivity: str
    origin_user_character_id: Optional[int] = None
    origin_character_name: Optional[str] = None
    shared_with: list[int] = Field(default_factory=list)
    shared_with_names: list[str] = Field(default_factory=list)
    created_at: datetime


class MemoryGrant(BaseModel):
    memory_id: int
    user_character_id: int


# --- Onboarding ------------------------------------------------------------ #
class OnboardingIn(BaseModel):
    acknowledged_ai: bool
    display_name: Optional[str] = None
    locale: Optional[str] = None


class OnboardingOut(BaseModel):
    ai_disclosure: str
    onboarding_completed: bool
    user_id: int
