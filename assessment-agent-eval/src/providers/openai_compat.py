"""OpenAI-compatible backend.

Works unchanged with Groq, OpenRouter, Together, local Ollama/LM Studio, and
OpenAI itself — switch by changing base_url + model + api_key_env in config.yaml.
"""

from __future__ import annotations

import os

from .base import LLMProvider


class OpenAICompatProvider(LLMProvider):
    name = "openai_compat"

    def __init__(self, config: dict):
        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover
            raise ImportError("openai not installed. Run: pip install openai") from e

        key_env = config.get("api_key_env", "OPENAI_API_KEY")
        api_key = os.environ.get(key_env)
        base_url = config.get("base_url") or None
        is_local = bool(base_url) and ("localhost" in base_url or "127.0.0.1" in base_url)
        if not api_key and not is_local:
            raise RuntimeError(
                f"Missing API key: set {key_env} in your .env (see .env.example)."
            )

        self.client = OpenAI(api_key=api_key or "not-needed", base_url=base_url)
        self.model_name = config.get("model", "llama-3.3-70b-versatile")
        self.temperature = float(config.get("temperature", 0))
        self.max_output_tokens = int(config.get("max_output_tokens", 2048))
        self.use_json_mode = bool(config.get("json_mode", True))
        self.last_usage = None
        self.last_finish_reason = None

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        kwargs = dict(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_output_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        if self.use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self.client.chat.completions.create(**kwargs)
        u = getattr(resp, "usage", None)
        if u is not None:
            self.last_usage = {
                "input_tokens": getattr(u, "prompt_tokens", 0) or 0,
                "output_tokens": getattr(u, "completion_tokens", 0) or 0,
                "thinking_tokens": 0,
                "total_tokens": getattr(u, "total_tokens", 0) or 0,
            }
        choice = resp.choices[0]
        self.last_finish_reason = getattr(choice, "finish_reason", None)
        return choice.message.content or ""
