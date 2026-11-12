"""Configuration, read once at startup from the environment.

This is the answer to open question 1 in docs/context/agent-contracts.md: where
the backend gets its provider, model and key from. Environment variables, loaded
from the repo-root .env in development and set by the host in a deployed
environment. Never from the eval's config.yaml, which is pinned for reproducible
eval runs and would tie the two together.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: The repository root, so paths below do not depend on the working directory.
ROOT = Path(__file__).resolve().parent.parent


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

    @field_validator("database_url")
    @classmethod
    def _asyncpg(cls, url: str) -> str:
        """Accept the URL the way a host hands it out.

        Render and most managed Postgres give `postgres://` or `postgresql://`,
        which SQLAlchemy reads as the synchronous psycopg driver. The app is
        async throughout, so the driver is named here rather than making whoever
        deploys remember to edit the URL. asyncpg also spells the TLS option
        `ssl`, not libpq's `sslmode`.
        """
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                url = "postgresql+asyncpg://" + url[len(prefix):]
        return url.replace("sslmode=", "ssl=")

    # --- LLM provider -----------------------------------------------------
    # Defaults to the offline stub. Every environment except production runs
    # this way, per docs/context/tech-stack.md, so nothing costs money by
    # accident.
    llm_provider: str = "mock"           # mock | gemini | openai_compat

    @field_validator("llm_provider")
    @classmethod
    def _blank_is_mock(cls, value: str) -> str:
        """An empty setting means the free stub, never a paid provider.

        A host's dashboard leaves a variable it was told about but not given as
        an empty string, which would otherwise reach the provider factory and be
        read as its own default, Gemini, and then fail for want of a key.
        """
        return value.strip().lower() or "mock"
    llm_model: str = "gemini-3.1-pro-preview"
    llm_api_key_env: str = "GEMINI_API_KEY"
    llm_temperature: float = 0.0
    llm_max_output_tokens: int = 4096
    llm_thinking_level: str | None = "low"

    # --- versions pinned per session --------------------------------------
    # Stamped on every session so a prompt or rubric change does not silently
    # alter what an old session meant.
    tutor_prompt_version: str = "v2"
    assessment_prompt_version: str = "v3"
    rubric_version: str = "v3"
    #: Describes a reading's figures at upload. Not pinned per session: what it
    #: writes is reviewed and saved as the reading's text, which is what counts.
    figure_prompt_version: str = "v1"

    # --- app ---------------------------------------------------------------
    environment: str = "local"   # local | development | production

    # --- the trial ------------------------------------------------------------
    # On only for the trial instance (docs/context/trial.md). One switch for the
    # whole set of rules: participants sign in by ID, one session each, a clock,
    # and classes in the control groups' modes. The server enforces every one.
    trial_mode: bool = False
    #: A participant's time, from the moment their reading opens.
    trial_minutes: int = 40

    # --- auth --------------------------------------------------------------
    # Google OAuth client, from the Google Cloud console. Sign-in is disabled
    # (real flow) when these are blank, but the dev bypass still works.
    google_client_id: str = ""
    google_client_secret: str = ""
    # Signs the session cookie. Must be a real random value in any deployed
    # environment; a blank one is only tolerable for the dev bypass locally.
    session_secret: str = "dev-insecure-change-me"
    # The public origin the browser uses, for building the OAuth redirect URI.
    # In dev the browser is on Vite (5173), which proxies /auth to the backend.
    app_base_url: str = "http://localhost:5173"
    # Comma-separated emails that sign in as instructors. Everyone else is a
    # student. The list is the source of truth; the role is written per login.
    instructor_emails: str = ""
    # Sign in as a seeded user without Google. Forced off in production.
    auth_dev_bypass: bool = True
    # Comma-separated emails that may switch to any seeded user after signing in
    # with Google, for QA on a deployed development environment where the open
    # sign-in picker would let anyone in. Ignored in production.
    qa_emails: str = ""

    # --- the built frontend -------------------------------------------------
    # Served by FastAPI when it exists, so a deploy is one service on one origin.
    # Absent in local development, where Vite serves the frontend instead.
    frontend_dist: Path = ROOT / "frontend" / "dist"

    @property
    def instructor_allowlist(self) -> set[str]:
        return {e.strip().lower() for e in self.instructor_emails.split(",") if e.strip()}

    @property
    def dev_bypass_enabled(self) -> bool:
        return self.auth_dev_bypass and self.environment != "production"

    @property
    def qa_allowlist(self) -> set[str]:
        if self.environment == "production":
            return set()
        return {e.strip().lower() for e in self.qa_emails.split(",") if e.strip()}

    @property
    def oauth_redirect_uri(self) -> str:
        return f"{self.app_base_url.rstrip('/')}/auth/callback"

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
