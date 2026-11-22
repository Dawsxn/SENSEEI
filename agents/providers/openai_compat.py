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
            self.last_usage = self._usage(u)
        choice = resp.choices[0]
        self.last_finish_reason = getattr(choice, "finish_reason", None)
        return choice.message.content or ""

    @staticmethod
    def _usage(u) -> dict:
        return {
            "input_tokens": getattr(u, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(u, "completion_tokens", 0) or 0,
            "thinking_tokens": 0,
            "total_tokens": getattr(u, "total_tokens", 0) or 0,
        }

    def _stream(self, messages: list[dict]):
        """Yield the reply's text as it arrives. Usage comes on the final chunk
        (`include_usage`), so `last_usage` holds it once the stream is exhausted.
        Prose only: the Tutor and the chatbot stream, the Assessment Agent never
        does, so no JSON mode here."""
        self.last_usage = None
        self.last_finish_reason = None
        for chunk in self.client.chat.completions.create(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_output_tokens,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        ):
            if getattr(chunk, "usage", None) is not None:
                self.last_usage = self._usage(chunk.usage)
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            if choice.finish_reason:
                self.last_finish_reason = choice.finish_reason
            text = getattr(choice.delta, "content", None)
            if text:
                yield text

    def stream(self, system_prompt: str, user_prompt: str):
        yield from self._stream([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])

    def chat_stream(self, turns: list[tuple[str, str]], system: str | None = None):
        """A real multi-turn conversation. `system`, when given, goes first as
        the system message (for the trial's chatbot, just the reading)."""
        head = [{"role": "system", "content": system}] if system else []
        yield from self._stream(head + [
            {"role": "user" if role == "user" else "assistant", "content": text}
            for role, text in turns
        ])
