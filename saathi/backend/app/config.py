"""Application configuration.

All secrets come from the environment. The Sarvam API key is NEVER read on the
client and never hard-coded here -- it is loaded from SARVAM_API_KEY.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ENV_FILE, ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # --- Core ---
    app_name: str = "Saathi"
    environment: str = "development"
    database_url: str = "sqlite:///./saathi.db"

    # --- Sarvam ---
    # Provider mode: "auto" (use Sarvam when a key is present, else mock),
    # "sarvam" (force live), "mock" (force offline).
    provider_mode: str = Field(default="auto")
    sarvam_api_key: str = Field(default="")
    sarvam_base_url: str = "https://api.sarvam.ai"

    # Current, supported Sarvam models (see docs.sarvam.ai).
    chat_model: str = "sarvam-105b-conversations"   # dialogue-tuned variant
    chat_model_general: str = "sarvam-105b"
    stt_model: str = "saaras:v4"                     # default / recommended ASR
    tts_model: str = "bulbul:v4-flash"               # latest TTS, persona voices
    tts_model_stable: str = "bulbul:v3"

    # --- Networking / limits ---
    request_timeout_s: float = 45.0
    max_history_turns: int = 16
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Privacy ---
    # When false (default) raw audio is never persisted to disk.
    persist_raw_audio: bool = False

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def use_live_provider(self) -> bool:
        if self.provider_mode == "mock":
            return False
        if self.provider_mode == "sarvam":
            return bool(self.sarvam_api_key)
        return bool(self.sarvam_api_key)  # auto


@lru_cache
def get_settings() -> Settings:
    return Settings()
