"""Write a provider failure's real reason to the server log.

A student or participant is only ever shown the error's type ("tutor failed:
ClientError"), which says nothing about why. The provider's own message does:
a model the API version does not serve, a key without billing, a rate limit. It
goes to the log, where the team reads it on the host, and never to the client.

An API key must never reach the log, so every key the settings name is scrubbed
from the message first, along with anything shaped like one.
"""

from __future__ import annotations

import logging
import os
import re

from ..settings import get_settings

log = logging.getLogger("senseei.provider")

#: Key-shaped strings, in case a provider echoes a key the settings do not name:
#: Google's (AIza...), OpenAI-style (sk-...), and long unbroken tokens.
_KEYLIKE = re.compile(r"AIza[0-9A-Za-z_\-]{20,}|sk-[0-9A-Za-z_\-]{8,}|[0-9A-Za-z_\-]{40,}")


def _secrets() -> list[str]:
    s = get_settings()
    names = {s.llm_api_key_env, s.figure_api_key_env, "GEMINI_API_KEY", "DEEPSEEK_API_KEY"}
    return [v for n in names if n and (v := os.environ.get(n))]


def scrub(text: str) -> str:
    for secret in _secrets():
        text = text.replace(secret, "[key]")
    return _KEYLIKE.sub("[key]", text)


def log_failure(where: str, error: BaseException | str) -> None:
    """Log why a provider call failed. `where` names the caller: tutor,
    assessment, chatbot, figures."""
    if isinstance(error, BaseException):
        detail = f"{type(error).__name__}: {error}"
    else:
        detail = str(error)
    # logging.config.fileConfig (Alembic's, when migrations run in the same
    # process) disables loggers that already exist. This one must never go quiet.
    log.disabled = False
    log.error("provider call failed (%s): %s", where, scrub(detail)[:2000])
