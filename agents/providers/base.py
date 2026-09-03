"""Provider interface. One method, so swapping backends never touches the agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    name: str = "base"
    # Set by complete() to the most recent call's token usage, or None if the
    # provider does not report it. Shape:
    #   {"input_tokens", "output_tokens", "thinking_tokens", "total_tokens"}
    last_usage: dict | None = None
    # Set by complete() to why the model stopped (e.g. "STOP", "MAX_TOKENS"), or None.
    last_finish_reason: str | None = None

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send the prompts to the model and return its raw text response.

        The response is expected to be a JSON object (parsing/validation happens
        in agent.parse_result, not here). Implementations should request JSON
        output where the provider supports it.
        """
        raise NotImplementedError

    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        """Yield the response in pieces as the model produces it.

        Used only for the Tutor Agent, whose prose the student watches appear.
        The Assessment Agent returns JSON parsed as a whole, so it never streams.

        The default is not really streaming: it calls `complete()` and yields the
        whole answer once, so a backend that does not support token streaming
        still works through this method. Providers that can stream override it
        and must still set `last_usage` / `last_finish_reason` when the stream
        ends, the same way `complete()` does.
        """
        text = self.complete(system_prompt, user_prompt)
        if text:
            yield text

    def describe(self) -> str:
        return getattr(self, "model_name", self.name)
