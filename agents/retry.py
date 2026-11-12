"""Provider call with rate-limit backoff, shared by both agents.

Free and preview tiers cap requests per minute and answer with a 429 rather than
queueing. Both agents therefore need the same behaviour: recognise the error,
honour the provider's own wait hint when it gives one, back off exponentially
when it does not, and give up cleanly rather than hammering a saturated quota.

Extracted from the Assessment Agent so the Tutor Agent does not carry a second
copy that can drift.
"""

from __future__ import annotations

import re
import time


def is_rate_limit(msg: str) -> bool:
    m = msg.lower()
    return ("429" in m or "rate limit" in m or "resource_exhausted" in m
            or "quota" in m or "exceeded" in m)


def retry_after_seconds(msg: str) -> float | None:
    """Pull a wait hint out of a provider error, if it gives one."""
    m = re.search(r"retry in ([\d.]+)\s*s", msg, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", msg)
    if m:
        return float(m.group(1))
    return None


def complete_with_backoff(provider, system_prompt: str, user_prompt: str,
                          max_rate_limit_retries: int = 3):
    """Call the provider, transparently waiting out rate-limit (429) errors.

    Returns (raw_text, None) on success or (None, error_message) on failure.
    """
    for attempt in range(max_rate_limit_retries + 1):
        try:
            return provider.complete(system_prompt, user_prompt), None
        except Exception as e:  # provider/network error
            msg = str(e)
            if is_rate_limit(msg) and attempt < max_rate_limit_retries:
                wait = retry_after_seconds(msg)
                if wait is None:
                    wait = min(60.0, 5.0 * (2 ** attempt))  # exponential fallback
                print(f"        rate limited — waiting {wait:.0f}s and retrying...",
                      flush=True)
                time.sleep(wait + 1)
                continue
            return None, f"Provider error: {e}"
    return None, "Provider error: rate-limit retries exhausted"


def stream_with_backoff(provider, system_prompt: str, user_prompt: str,
                        max_rate_limit_retries: int = 3):
    """Stream the provider's reply, waiting out a rate limit before the first chunk.

    A generator that yields text chunks. A 429 almost always surfaces as the
    stream is established (before any chunk arrives), so this retries the whole
    stream on that. Once chunks are flowing a mid-stream failure is raised, since
    partial output has already been sent and cannot be cleanly retried.
    """
    for attempt in range(max_rate_limit_retries + 1):
        started = False
        try:
            for chunk in provider.stream(system_prompt, user_prompt):
                started = True
                yield chunk
            return
        except Exception as e:
            msg = str(e)
            if not started and is_rate_limit(msg) and attempt < max_rate_limit_retries:
                wait = retry_after_seconds(msg)
                if wait is None:
                    wait = min(60.0, 5.0 * (2 ** attempt))
                time.sleep(wait + 1)
                continue
            raise
