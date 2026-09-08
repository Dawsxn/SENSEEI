"""Google OAuth wiring and the rules around who may sign in.

Sign-in is Google OAuth restricted to DLSU addresses, enforced here in code (the
Google project is a personal one, so the domain rule cannot be Google's own
"internal" setting). Instructor status comes from a config allowlist, not the
database, and is re-derived on every login.
"""

from __future__ import annotations

from functools import lru_cache

from authlib.integrations.starlette_client import OAuth

from .settings import get_settings

DLSU_DOMAIN = "dlsu.edu.ph"


@lru_cache
def google_oauth() -> OAuth:
    """The Authlib OAuth registry with Google configured, built once."""
    s = get_settings()
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=s.google_client_id,
        client_secret=s.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


def is_dlsu_email(email: str) -> bool:
    return email.strip().lower().endswith(f"@{DLSU_DOMAIN}")


def is_instructor(email: str) -> bool:
    return email.strip().lower() in get_settings().instructor_allowlist
