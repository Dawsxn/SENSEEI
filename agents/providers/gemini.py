"""Google Gemini backend, on the official `google-genai` SDK.

`google-genai` is Google's current GA SDK (the older `google-generativeai` is
deprecated as of 2025-11-30). This backend:
  - requests JSON output by default (response_mime_type=application/json), which
    `json_mode: false` turns off for agents that return prose,
  - supports Gemini 3.x reasoning control via `thinking_level`
    (minimal | low | medium | high),
  - records per-call token usage (incl. thinking tokens) in `self.last_usage`.
"""

from __future__ import annotations

import os

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, config: dict):
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "google-genai not installed. Run: pip install google-genai"
            ) from e
        self._genai = genai
        self._types = types

        key_env = config.get("api_key_env", "GEMINI_API_KEY")
        api_key = os.environ.get(key_env)
        if not api_key:
            raise RuntimeError(
                f"Missing API key: set {key_env} in your .env (see .env.example)."
            )
        self.client = genai.Client(api_key=api_key)

        self.model_name = config.get("model", "gemini-3.1-pro-preview")
        self.temperature = float(config.get("temperature", 0))
        self.max_output_tokens = int(config.get("max_output_tokens", 8192))
        # minimal | low | medium | high (Gemini 3.x). Blank/None -> model default.
        self.thinking_level = config.get("thinking_level") or None
        # The Assessment Agent returns JSON; the Tutor Agent returns prose.
        self.json_mode = bool(config.get("json_mode", True))
        self.last_usage = None
        self.last_finish_reason = None

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        types = self._types
        cfg_kwargs = dict(
            system_instruction=system_prompt,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
        )
        if self.json_mode:
            cfg_kwargs["response_mime_type"] = "application/json"
        if self.thinking_level:
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=self.thinking_level
            )
        resp = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(**cfg_kwargs),
        )
        self.last_usage = self._usage(resp)
        self.last_finish_reason = self._finish_reason(resp)
        return resp.text or ""

    def stream(self, system_prompt: str, user_prompt: str):
        """Yield text chunks as Gemini generates them.

        Usage and finish reason arrive on the streamed chunks (the totals land on
        the last one), so `last_usage` / `last_finish_reason` are updated as the
        stream runs and hold the final values once it is exhausted.
        """
        types = self._types
        cfg_kwargs = dict(
            system_instruction=system_prompt,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
        )
        if self.json_mode:
            cfg_kwargs["response_mime_type"] = "application/json"
        if self.thinking_level:
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=self.thinking_level
            )
        self.last_usage = None
        self.last_finish_reason = None
        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(**cfg_kwargs),
        ):
            usage = self._usage(chunk)
            if usage is not None:
                self.last_usage = usage
            reason = self._finish_reason(chunk)
            if reason is not None:
                self.last_finish_reason = reason
            text = getattr(chunk, "text", None)
            if text:
                yield text

    @staticmethod
    def _usage(resp) -> dict | None:
        um = getattr(resp, "usage_metadata", None)
        if um is None:
            return None

        def n(attr):
            v = getattr(um, attr, None)
            return int(v) if v is not None else 0

        return {
            "input_tokens": n("prompt_token_count"),
            "output_tokens": n("candidates_token_count"),
            "thinking_tokens": n("thoughts_token_count"),
            "total_tokens": n("total_token_count"),
        }

    @staticmethod
    def _finish_reason(resp) -> str | None:
        cands = getattr(resp, "candidates", None) or []
        if not cands:
            return None
        fr = getattr(cands[0], "finish_reason", None)
        if fr is None:
            return None
        return getattr(fr, "name", None) or str(fr)
