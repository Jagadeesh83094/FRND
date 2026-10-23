"""Live Sarvam AI provider.

Endpoints (docs.sarvam.ai):
  chat  POST {base}/v1/chat/completions        header: api-subscription-key
  stt   POST {base}/speech-to-text             multipart/form-data
  tts   POST {base}/text-to-speech             JSON, returns base64 audio

The API key is read from settings (env) and is never exposed to the client.
"""
from __future__ import annotations

import base64

import httpx

from ..config import get_settings
from .base import BaseProvider, ChatResult, ProviderError, ProviderErrorKind, STTResult, TTSResult


class SarvamProvider(BaseProvider):
    name = "sarvam"
    is_live = True

    def __init__(self, api_key: str, base_url: str, timeout_s: float = 45.0):
        self._key = api_key
        self._base = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=timeout_s,
            headers={"api-subscription-key": api_key},
        )

    # ------------------------------------------------------------------ #
    async def aclose(self) -> None:
        await self._client.aclose()

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code < 400:
            return
        code = resp.status_code
        if code in (401, 403):
            kind = ProviderErrorKind.AUTH
        elif code == 402:
            kind = ProviderErrorKind.CREDITS
        elif code == 429:
            kind = ProviderErrorKind.RATE_LIMIT
        elif 400 <= code < 500:
            kind = ProviderErrorKind.BAD_REQUEST
        elif code >= 500:
            kind = ProviderErrorKind.SERVER
        else:
            kind = ProviderErrorKind.UNKNOWN
        detail = ""
        try:
            detail = resp.text[:300]
        except Exception:  # pragma: no cover
            pass
        raise ProviderError(kind, f"Sarvam returned {code}: {detail}", status_code=code)

    async def _request(self, method: str, url: str, **kwargs):
        try:
            return await self._client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise ProviderError(ProviderErrorKind.TIMEOUT, str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(ProviderErrorKind.NETWORK, str(exc)) from exc

    # ------------------------------------------------------------------ #
    async def chat(
        self,
        messages: list[dict],
        *,
        model: str,
        max_tokens: int = 200,
        temperature: float = 0.8,
    ) -> ChatResult:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        resp = await self._request("POST", f"{self._base}/v1/chat/completions", json=payload)
        self._raise_for_status(resp)
        data = resp.json()
        try:
            choice = data["choices"][0]["message"]
            text = choice.get("content") or ""
        except (KeyError, IndexError) as exc:
            raise ProviderError(ProviderErrorKind.UNKNOWN, f"Unexpected chat response: {data}") from exc
        usage = data.get("usage") or {}
        return ChatResult(text=text, tokens=usage.get("completion_tokens"), model=model, raw=data)

    async def transcribe(
        self,
        audio: bytes,
        *,
        filename: str,
        language_code: str,
        model: str,
        mode: str = "transcribe",
    ) -> STTResult:
        mime = "audio/wav"
        lower = (filename or "").lower()
        if lower.endswith(".webm"):
            mime = "audio/webm"
        elif lower.endswith(".mp3"):
            mime = "audio/mpeg"
        elif lower.endswith(".ogg"):
            mime = "audio/ogg"
        elif lower.endswith(".m4a"):
            mime = "audio/mp4"

        files = {"file": (filename or "audio.wav", audio, mime)}
        data = {"model": model, "language_code": language_code, "mode": mode}
        resp = await self._request(
            "POST", f"{self._base}/speech-to-text", files=files, data=data
        )
        self._raise_for_status(resp)
        body = resp.json()
        return STTResult(
            text=body.get("transcript", ""),
            language_code=body.get("language_code", language_code),
            mode=mode,
            raw=body,
        )

    async def synthesize(
        self,
        text: str,
        *,
        language_code: str,
        speaker_id: str,
        model: str,
        pace: float = 1.0,
        sample_rate: int = 22050,
    ) -> TTSResult:
        payload = {
            "text": text,
            "language_code": language_code,
            "model": model,
            "speaker": speaker_id,
            "pace": pace,
            "speech_sample_rate": sample_rate,
            "enable_preprocessing": True,
        }
        resp = await self._request("POST", f"{self._base}/text-to-speech", json=payload)
        self._raise_for_status(resp)
        body = resp.json()
        audios = body.get("audios") or []
        if not audios:
            raise ProviderError(ProviderErrorKind.UNKNOWN, "TTS returned no audio")
        audio = base64.b64decode(audios[0])
        return TTSResult(
            audio=audio,
            mime_type="audio/wav",
            sample_rate=sample_rate,
            speaker_id=speaker_id,
            model=model,
            raw={"request_id": body.get("request_id")},
        )
