"""Voice routes: STT, TTS and voice preview."""
from __future__ import annotations

import base64
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import CharacterDefinition, User
from ..providers import ProviderError, get_provider
from ..rate_limit import enforce_rate_limit
from ..schemas import STTOut, TTSOut, TTSRequest
from ..services import character_service, voice_service
from .deps import get_current_user

router = APIRouter(prefix="/api", tags=["voice"])

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB guard


@router.get("/voice/config")
def voice_config():
    settings = get_settings()
    provider = get_provider()
    return {
        "provider": provider.name,
        "live": provider.is_live,
        "chat_model": settings.chat_model,
        "stt_model": settings.stt_model,
        "tts_model": settings.tts_model,
        "note": (
            "Turn-based voice: each turn uploads recorded audio, transcribes it, "
            "then plays back synthesized speech. This is not continuous real-time audio."
            if not provider.is_live else
            "Turn-based voice pipeline backed by live Sarvam models."
        ),
    }


@router.post("/voice/transcribe", response_model=STTOut)
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form(default="en-IN"),
    mode: str = Form(default="transcribe"),
    _user: User = Depends(get_current_user),
):
    enforce_rate_limit(request, bucket="transcription", limit=10)
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=422, detail="Empty audio")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio too large (max 10 MB)")
    started = time.perf_counter()
    try:
        result = await voice_service.transcribe(
            audio, filename=file.filename or "audio.wav", language=language, mode=mode
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail={"kind": exc.kind, "message": exc.user_message()})
    finally:
        del audio
    return {
        "text": result.text,
        "language_code": result.language_code,
        "mode": result.mode,
        "provider": get_provider().name,
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }


def _definition(db: Session, character_id: str) -> CharacterDefinition:
    definition = db.get(CharacterDefinition, character_id)
    if definition is None or not definition.is_active:
        raise HTTPException(status_code=404, detail="Character not found")
    return definition


async def _tts_response(db, user, character_id, text, language) -> dict:
    definition = _definition(db, character_id)
    uc = character_service.get_or_create_user_character(db, user, character_id)
    started = time.perf_counter()
    try:
        tts, voice = await voice_service.synthesize(db, definition, uc, text, language)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail={"kind": exc.kind, "message": exc.user_message()})
    return {
        "audio_base64": base64.b64encode(tts.audio).decode("ascii"),
        "mime_type": tts.mime_type,
        "speaker_id": voice["speaker_id"],
        "model": voice["model"],
        "language_code": voice["language_code"],
        "is_fallback": voice.get("is_fallback", False),
        "fallback_reason": voice.get("fallback_reason"),
        "provider": get_provider().name,
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }


@router.post("/characters/{character_id}/tts", response_model=TTSOut)
async def tts(
    character_id: str,
    payload: TTSRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(request, bucket="tts", limit=20)
    if not payload.text.strip():
        raise HTTPException(status_code=422, detail="Empty text")
    if len(payload.text) > 5000:
        raise HTTPException(status_code=413, detail="Text too long (max 5000 characters)")
    return await _tts_response(db, user, character_id, payload.text.strip(), payload.language)


@router.get("/characters/{character_id}/voice-preview", response_model=TTSOut)
async def voice_preview(
    character_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A short spoken sample so the user can hear the character's voice."""
    enforce_rate_limit(request, bucket="voice-preview", limit=20)
    definition = _definition(db, character_id)
    uc = character_service.get_or_create_user_character(db, user, character_id)
    sample = (definition.example_greeting or "Hi, it's good to see you.")[:180]
    return await _tts_response(db, user, character_id, sample, (uc.language_prefs or [None])[0])
