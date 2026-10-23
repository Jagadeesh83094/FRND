"""Voice pipeline tests (requirements C, D, E, J)."""
from __future__ import annotations

import base64
import io
import wave


def _tiny_wav() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 1600)  # 0.1s silence
    return buf.getvalue()


def test_voice_config_reports_turn_based_and_provider(client):
    cfg = client.get("/api/voice/config").json()
    assert cfg["provider"] == "mock"
    assert "Turn-based" in cfg["note"] or "turn-based" in cfg["note"].lower()


def test_voice_preview_returns_playable_audio(client, user_headers):
    r = client.get("/api/characters/mom/voice-preview", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["speaker_id"] == "aparna_en_companion"
    audio = base64.b64decode(body["audio_base64"])
    assert audio[:4] == b"RIFF"  # a real WAV container
    assert len(audio) > 1000


def test_tts_endpoint_synthesizes_text(client, user_headers):
    r = client.post(
        "/api/characters/dad/tts",
        json={"text": "Let's think it through calmly."},
        headers=user_headers,
    )
    assert r.status_code == 200
    assert base64.b64decode(r.json()["audio_base64"])[:4] == b"RIFF"


def test_transcribe_accepts_audio_and_returns_text(client):
    files = {"file": ("clip.wav", _tiny_wav(), "audio/wav")}
    data = {"language": "en-IN", "mode": "transcribe"}
    r = client.post("/api/voice/transcribe", files=files, data=data)
    assert r.status_code == 200
    assert r.json()["text"]


def test_chat_turn_can_include_audio(client, user_headers):
    out = client.post(
        "/api/characters/mentor/chat",
        json={"text": "I'm feeling stuck.", "mode": "voice", "speak": True},
        headers=user_headers,
    ).json()
    assert out["audio_base64"]
    assert base64.b64decode(out["audio_base64"])[:4] == b"RIFF"


def test_sanitizer_strips_markdown_for_speech():
    from app.prompts import sanitize_for_speech

    raw = "## Heading\n- **Bold point**\n1. item\n[link](http://x)"
    out = sanitize_for_speech(raw)
    assert "#" not in out and "*" not in out and "[" not in out
    assert "Bold point" in out
