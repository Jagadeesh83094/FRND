"""Provider factory."""
from __future__ import annotations

from ..config import get_settings
from .base import (
    BaseProvider,
    ChatResult,
    ProviderError,
    ProviderErrorKind,
    STTResult,
    TTSResult,
)
from .mock import MockProvider
from .sarvam import SarvamProvider

_provider: BaseProvider | None = None


def get_provider() -> BaseProvider:
    """Return the active provider.

    Uses Sarvam when a key is present and provider_mode allows it; otherwise the
    offline mock, so the app always runs.
    """
    global _provider
    settings = get_settings()
    # If the provider mode changed or wasn't set, re-instantiate
    if _provider is not None:
        if settings.use_live_provider == _provider.is_live:
            return _provider
    
    if settings.use_live_provider:
        _provider = SarvamProvider(
            api_key=settings.sarvam_api_key,
            base_url=settings.sarvam_base_url,
            timeout_s=settings.request_timeout_s,
        )
    else:
        _provider = MockProvider()
    return _provider


def reset_provider() -> None:
    """Test hook: drop the cached provider so settings changes take effect."""
    global _provider
    _provider = None


__all__ = [
    "BaseProvider",
    "ChatResult",
    "STTResult",
    "TTSResult",
    "ProviderError",
    "ProviderErrorKind",
    "MockProvider",
    "SarvamProvider",
    "get_provider",
    "reset_provider",
]
