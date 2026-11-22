"""OpenAI-compatible backend.

Works unchanged with Groq, OpenRouter, Together, local Ollama/LM Studio, and
OpenAI itself — switch by changing base_url + model + api_key_env in config.yaml.
"""

from __future__ import annotations

import json
import os

from .base import LLMProvider

#: DeepSeek's server-side web search (api-docs.deepseek.com/guides/web_tools).
#: The model decides when to search; nothing runs on our side. Its record of the
#: searches (`server_tool_calls`) and the citations (`annotations`) arrive on the
#: last chunk, and the record must be sent back with that reply on later turns.
WEB_SEARCH_TOOL = {"type": "deepseek_web_search"}


def _extra(obj, name: str):
    """A field the SDK doesn't model, read off a response object."""
    if obj is None:
        return None
    value = getattr(obj, name, None)
    if value is None:
        value = (getattr(obj, "model_extra", None) or {}).get(name)
    return value


def _plain(value):
    """SDK objects to plain JSON values, so they can be stored and sent back."""
    return json.loads(json.dumps(value, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o)))


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

    def _stream(self, messages: list[dict], tools: list[dict] | None = None, found: dict | None = None):
        """Yield the reply's text as it arrives. Usage comes on the final chunk
        (`include_usage`), so `last_usage` holds it once the stream is exhausted.
        Prose only: the Tutor and the chatbot stream, the Assessment Agent never
        does, so no JSON mode here.

        With `tools`, any server-side tool record (`server_tool_calls`) and
        citations (`annotations`) are put in `found` as plain JSON. A dict the
        caller passes, not state on the provider, which is shared between
        requests."""
        self.last_usage = None
        self.last_finish_reason = None
        kwargs = dict(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_output_tokens,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )
        if tools:
            kwargs["tools"] = tools
        for chunk in self.client.chat.completions.create(**kwargs):
            if getattr(chunk, "usage", None) is not None:
                self.last_usage = self._usage(chunk.usage)
            if found is not None:
                for where in (chunk, *(chunk.choices or [])):
                    for holder in (where, _extra(where, "delta"), _extra(where, "message")):
                        for name in ("server_tool_calls", "annotations"):
                            value = _extra(holder, name)
                            if value:
                                found[name] = _plain(value)
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

    def chat_stream(
        self,
        turns: list[tuple],
        system: str | None = None,
        web_search: bool = False,
        found: dict | None = None,
    ):
        """A real multi-turn conversation. `system`, when given, goes first as
        the system message (for the trial's chatbot, just the reading). With
        `web_search`, the model may search the web (DeepSeek's server tool); an
        earlier reply's record of its searches comes as the turn's third item
        and is sent back with it, as the API requires."""
        head = [{"role": "system", "content": system}] if system else []
        messages = []
        for role, text, *rest in turns:
            message = {"role": "user" if role == "user" else "assistant", "content": text}
            extra = rest[0] if rest else None
            if web_search and role != "user" and extra and extra.get("server_tool_calls"):
                message["server_tool_calls"] = extra["server_tool_calls"]
            messages.append(message)
        yield from self._stream(
            head + messages, tools=[WEB_SEARCH_TOOL] if web_search else None, found=found
        )
