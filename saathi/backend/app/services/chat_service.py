"""Chat turn orchestration: context assembly -> provider -> persistence -> speech."""
from __future__ import annotations

import base64
import time

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import CharacterDefinition, User, UserCharacter
from ..prompts import build_system_prompt, max_tokens_for, sanitize_for_speech
from ..providers import ProviderError, get_provider
from ..safety import check_message
from . import character_service, conversation_service, memory_service, voice_service


def _definition(db: Session, uc: UserCharacter) -> CharacterDefinition:
    definition = db.get(CharacterDefinition, uc.character_definition_id) if uc.character_definition_id else None
    if definition is None:
        raise ValueError("Character definition missing")
    return definition


async def greeting(db: Session, user: User, uc: UserCharacter, *, speak: bool = False) -> dict:
    """The character's opening line, in its own voice."""
    definition = _definition(db, uc)
    character = character_service.character_to_dict(db, definition, uc)
    text = definition.example_greeting or "Hi, I'm here."
    language = (uc.language_prefs or [None])[0]
    convo = conversation_service.get_or_create_active_conversation(db, user, uc)
    msg = conversation_service.add_message(
        db, convo, role="assistant", content=text, language=language, meta={"greeting": True}
    )
    out = {
        "reply": text, "message_id": msg.id, "conversation_id": convo.id,
        "character_id": definition.id, "character_name": character["display_name"],
        "language": language, "crisis": {"flagged": False, "resources": []},
        "memories_used": [], "audio_base64": None, "audio_mime": None,
        "voice": character["voice"], "provider": get_provider().name,
    }
    if speak:
        await _attach_audio(db, definition, uc, out, text, language)
    return out


async def run_turn(
    db: Session,
    user: User,
    uc: UserCharacter,
    text: str,
    *,
    mode: str = "text",
    language: str | None = None,
    speak: bool = False,
) -> dict:
    started = time.perf_counter()
    definition = _definition(db, uc)
    character = character_service.character_to_dict(db, definition, uc)

    crisis = check_message(text)
    memories = memory_service.memory_content_for_prompt(db, uc)
    lang = language or (uc.language_prefs or [None])[0]

    persona = {
        "display_name": definition.display_name,
        "personality_description": character["personality_description"],
        "conversational_style": character["conversational_style"],
        "tone": definition.tone or {},
        "behaviors": definition.behaviors or [],
        "do_list": definition.do_list or [],
        "dont_list": definition.dont_list or [],
    }
    system_prompt = build_system_prompt(
        character=persona,
        display_name=character["display_name"],
        language=lang or (definition.languages or ["en-IN"])[0],
        response_length=character["response_length"],
        memories=memories,
        is_crisis=crisis.is_crisis,
    )

    convo = conversation_service.get_or_create_active_conversation(db, user, uc)
    conversation_service.add_message(db, convo, role="user", content=text, language=lang,
                                     meta={"mode": mode})

    history = conversation_service.history_for_prompt(db, convo, get_settings().max_history_turns)
    messages = [{"role": "system", "content": system_prompt}, *history]

    provider = get_provider()
    settings = get_settings()
    try:
        result = await provider.chat(
            messages,
            model=settings.chat_model,
            max_tokens=max_tokens_for(character["response_length"]),
            temperature=0.8,
        )
    except ProviderError as exc:
        # Record a soft error and re-raise for the router to translate.
        raise

    reply = sanitize_for_speech(result.text) or "..."

    assistant_msg = conversation_service.add_message(
        db, convo, role="assistant", content=reply, language=lang,
        meta={"mode": mode, "memories_used": memories, "crisis": crisis.is_crisis,
              "provider": provider.name},
    )

    out = {
        "reply": reply,
        "message_id": assistant_msg.id,
        "conversation_id": convo.id,
        "character_id": definition.id,
        "character_name": character["display_name"],
        "language": lang,
        "crisis": {"flagged": crisis.is_crisis, "resources": crisis.resources},
        "memories_used": memories,
        "audio_base64": None,
        "audio_mime": None,
        "voice": character["voice"],
        "provider": provider.name,
    }
    if speak:
        await _attach_audio(db, definition, uc, out, reply, lang)

    out["latency_ms"] = int((time.perf_counter() - started) * 1000)
    return out


async def _attach_audio(db, definition, uc, out: dict, text: str, language) -> None:
    try:
        tts, voice = await voice_service.synthesize(db, definition, uc, text, language)
        out["audio_base64"] = base64.b64encode(tts.audio).decode("ascii")
        out["audio_mime"] = tts.mime_type
        out["voice"] = {
            "provider": voice["provider"], "model": voice["model"],
            "speaker_id": voice["speaker_id"], "language_code": voice["language_code"],
            "pace": voice["pace"], "fallback_speaker": voice.get("fallback_speaker"),
            "config_version": voice.get("config_version", 1),
            "is_fallback": voice.get("is_fallback", False),
            "fallback_reason": voice.get("fallback_reason"),
        }
    except ProviderError:
        # Text still succeeds even if speech fails.
        out["audio_base64"] = None
