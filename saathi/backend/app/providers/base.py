"""Provider abstraction: chat, speech-to-text and text-to-speech.

Both the live Sarvam provider and the offline mock implement this interface, so
the rest of the app never talks to a vendor directly (requirement D).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ProviderErrorKind:
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    CREDITS = "credits_exhausted"
    BAD_REQUEST = "bad_request"
    AUTH = "auth"
    SERVER = "server"
    UNKNOWN = "unknown"


class ProviderError(Exception):
    def __init__(self, kind: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.message = message

    def user_message(self) -> str:
        return {
            ProviderErrorKind.TIMEOUT: "That took a little too long. Want to try again?",
            ProviderErrorKind.RATE_LIMIT: "I'm getting a lot of requests right now. Give me a moment?",
            ProviderErrorKind.NETWORK: "I couldn't reach the service just now. Try once more?",
            ProviderErrorKind.CREDITS: "The voice service is out of credits right now.",
            ProviderErrorKind.BAD_REQUEST: "Something in that request didn't go through.",
            ProviderErrorKind.AUTH: "The voice service isn't configured correctly.",
            ProviderErrorKind.SERVER: "The service had a hiccup. Try again in a moment?",
        }.get(self.kind, "Something went wrong on my side. Try again?")


@dataclass
class ChatResult:
    text: str
    tokens: int | None = None
    model: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class STTResult:
    text: str
    language_code: str | None = None
    mode: str = "transcribe"
    raw: dict = field(default_factory=dict)


@dataclass
class TTSResult:
    audio: bytes
    mime_type: str = "audio/wav"
    sample_rate: int = 22050
    speaker_id: str | None = None
    model: str | None = None
    raw: dict = field(default_factory=dict)


class BaseProvider(ABC):
    name: str = "base"
    is_live: bool = False

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        *,
        model: str,
        max_tokens: int = 200,
        temperature: float = 0.8,
    ) -> ChatResult: ...

    @abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        *,
        filename: str,
        language_code: str,
        model: str,
        mode: str = "transcribe",
    ) -> STTResult: ...

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        *,
        language_code: str,
        speaker_id: str,
        model: str,
        pace: float = 1.0,
        sample_rate: int = 22050,
    ) -> TTSResult: ...

    async def aclose(self) -> None:  # pragma: no cover - optional cleanup
        return None
