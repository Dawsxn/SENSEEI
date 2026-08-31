"""Configuration, read once at startup from the environment.

This is the answer to open question 1 in docs/context/agent-contracts.md: where
the backend gets its provider, model and key from. Environment variables, loaded
from the repo-root .env in development and set by the host in a deployed
environment. Never from the eval's config.yaml, which is pinned for reproducible
eval runs and would tie the two together.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # .env also holds keys the eval uses
        case_sensitive=False,
    )

    # --- database ---------------------------------------------------------
    # asyncpg, not psycopg: the app is async all the way down so a request
    # waiting on the database does not hold a worker.
    database_url: str = "postgresql+asyncpg://senseei:senseei@localhost:5432/senseei"
    db_echo: bool = False        # log every statement; noisy, useful when stuck

    # --- LLM provider -----------------------------------------------------
    # Defaults to the offline stub. Every environment except production runs
    # this way, per docs/context/tech-stack.md, so nothing costs money by
    # accident.
    llm_provider: str = "mock"           # mock | gemini | openai_compat
    llm_model: str = "gemini-3.1-pro-preview"
    llm_api_key_env: str = "GEMINI_API_KEY"
    llm_temperature: float = 0.0
    llm_max_output_tokens: int = 4096
    llm_thinking_level: str | None = "low"

    # --- versions pinned per session --------------------------------------
    # Stamped on every session so a prompt or rubric change does not silently
    # alter what an old session meant.
    tutor_prompt_version: str = "v1"
    assessment_prompt_version: str = "v3"
    rubric_version: str = "v3"

    # --- app ---------------------------------------------------------------
    environment: str = "local"   # local | development | production

    def provider_config(self) -> dict:
        """The dict agents.providers.get_provider() expects."""
        return {
            "provider": self.llm_provider,
            "model": self.llm_model,
            "api_key_env": self.llm_api_key_env,
            "temperature": self.llm_temperature,
            "max_output_tokens": self.llm_max_output_tokens,
            "thinking_level": self.llm_thinking_level,
        }


@lru_cache
def get_settings() -> Settings:
    """Cached, so the env is read once rather than per request."""
    return Settings()
