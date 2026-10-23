"""Voice service: resolves a character's voice and drives TTS / STT."""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import CharacterDefinition, UserCharacter, VoiceConfiguration
from ..providers import ProviderError, TTSResult, get_provider
from ..voice_catalog import resolve_voice


def resolve_voice_for(
    db: Session, definition: CharacterDefinition, uc: UserCharacter, language: str | None = None
) -> dict:
    """Resolve the voice for a character in a given language, with fallback info."""
    # A pinned user override wins.
    if uc.voice_config_id:
        vc = db.get(VoiceConfiguration, uc.voice_config_id)
        if vc:
            return {
                "provider": vc.provider, "model": vc.model, "speaker_id": vc.speaker_id,
                "language_code": vc.language_code, "pace": vc.pace,
                "fallback_speaker": vc.fallback_speaker, "config_version": vc.config_version,
                "is_fallback": False, "fallback_reason": None,
            }
    lang = language or (uc.language_prefs or [None])[0] or (definition.languages or ["en-IN"])[0]
    resolved = resolve_voice(definition.id, lang)
    return {
        "provider": "sarvam", "model": resolved["model"], "speaker_id": resolved["speaker_id"],
        "language_code": resolved["language_code"], "pace": resolved["pace"],
        "fallback_speaker": None, "config_version": 1,
        "is_fallback": resolved["fallback"] is not None,
        "fallback_reason": (resolved["fallback"] or {}).get("reason"),
    }


async def synthesize(
    db: Session,
    definition: CharacterDefinition,
    uc: UserCharacter,
    text: str,
    language: str | None = None,
) -> tuple[TTSResult, dict]:
    voice = resolve_voice_for(db, definition, uc, language)
    provider = get_provider()
    try:
        result = await provider.synthesize(
            text,
            language_code=voice["language_code"],
            speaker_id=voice["speaker_id"],
            model=voice["model"],
            pace=voice["pace"],
        )
    except ProviderError as exc:
        # If a live persona is rejected, retry once on the stable v3 voice.
        if exc.kind == "bad_request" and voice["model"] != get_settings().tts_model_stable:
            settings = get_settings()
            from ..voice_catalog import v3_fallback_for
            model, speaker = v3_fallback_for(voice["language_code"])
            result = await provider.synthesize(
                text, language_code=voice["language_code"], speaker_id=speaker,
                model=model, pace=voice["pace"],
            )
            voice = dict(voice, model=model, speaker_id=speaker, is_fallback=True,
                         fallback_reason="persona_rejected")
        else:
            raise
    return result, voice


async def transcribe(audio: bytes, *, filename: str, language: str, mode: str = "transcribe"):
    provider = get_provider()
    settings = get_settings()
    return await provider.transcribe(
        audio, filename=filename, language_code=language,
        model=settings.stt_model, mode=mode,
    )


def now_ms() -> float:
    return time.perf_counter() * 1000.0
