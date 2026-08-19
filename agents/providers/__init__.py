"""Swappable LLM provider backends.

Add a new backend by implementing `LLMProvider.complete()` (see base.py) and
wiring it into `get_provider()`. Selecting a provider is a config-only change.
"""

from __future__ import annotations

from .base import LLMProvider


def get_provider(config: dict) -> LLMProvider:
    """Instantiate the provider named in config['provider']."""
    provider = (config.get("provider") or "gemini").strip().lower()
    if provider == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(config)
    if provider in ("openai_compat", "openai", "groq", "openrouter", "together", "ollama"):
        from .openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(config)
    if provider == "mock":
        from .mock import MockProvider
        return MockProvider(config)
    raise ValueError(
        f"Unknown provider: {provider!r}. Use one of: gemini, openai_compat, mock."
    )
