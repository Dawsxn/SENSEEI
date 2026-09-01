"""The unguided-LLM arm: a general-purpose chat, no scaffolding of any kind.

Section 4.6.2 specifies "a general-purpose LLM chat interface with no pedagogical
system prompt and no constraint on how the tool is used", powered by the same
underlying model as SENSEE-I's agents. This arm represents the unguided use
characterised in Section 2.1, and it is the comparison that isolates the SEE-I
scaffolding: if it ran a weaker model, a difference in outcomes would be
explained by capability rather than by the framework, and the study's central
claim would not follow.

**No model is baked in.** Everything reaches the provider through
``agents/providers/``, so which model the arm runs is a line in ``trial.yaml``.
That matters beyond tidiness: the model currently pinned is a preview model,
preview models carry lower and less predictable rate limits than
general-availability ones, and a single-sitting trial puts thirty participants on
the provider at once. Swapping to a different model, or a different provider
entirely, must not be a code change — and here it is not.

**The seam is :class:`ChatBackend`, not the provider.** The shared provider
interface is single-turn: ``complete(system_prompt, user_prompt)``. A chat is not.
:class:`ProviderChatBackend` bridges the two by rendering the transcript into the
user prompt, which works against every provider the repo has and required no
change to the agent code the eval harness measures.

That bridge is an approximation, and worth being honest about: a provider given
structured messages applies its own chat template, which flattening does not
reproduce exactly. It is the same model either way, so the parity requirement of
Section 4.6.2 holds, but if native multi-turn fidelity later matters, a second
``ChatBackend`` implementation slots in behind the same protocol without touching
anything in this module or above it. That is what the protocol is for.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable

from .conversation import Conversation, Speaker, Turn

#: Section 4.6.2, taken literally: no pedagogical system prompt. Not a neutral
#: one, not a short one — none. Any instruction here would be scaffolding, which
#: is the variable under test.
NO_SYSTEM_PROMPT = ""


class ChatBackendError(RuntimeError):
    """The model could not be reached, or refused to answer."""


@runtime_checkable
class ChatBackend(Protocol):
    """Somewhere to send a conversation and get the next reply."""

    def reply(self, conversation: Conversation) -> str:
        """The model's next message, given everything said so far."""
        ...

    @property
    def fingerprint(self) -> str:
        """``"<provider>:<model>"``, for the parity check and for provenance."""
        ...


class ProviderChatBackend:
    """Runs a conversation through any provider in ``agents/providers/``.

    Construct it from :meth:`study.trial_config.LLMConfig.provider_settings`, so
    the arm's model is whatever the trial pins and nothing here has to know which
    one that is.
    """

    def __init__(self, settings: dict, max_rate_limit_retries: int = 3):
        from agents.providers import get_provider

        self._settings = dict(settings)
        self._provider = get_provider(self._settings)
        self._max_rate_limit_retries = max_rate_limit_retries

    @property
    def fingerprint(self) -> str:
        provider = self._settings.get("provider", "gemini")
        return f"{provider}:{self._provider.describe()}"

    def reply(self, conversation: Conversation) -> str:
        from agents.retry import complete_with_backoff

        text, error = complete_with_backoff(
            self._provider,
            NO_SYSTEM_PROMPT,
            self._render(conversation),
            max_rate_limit_retries=self._max_rate_limit_retries,
        )
        if error is not None:
            raise ChatBackendError(error)
        if not (text or "").strip():
            raise ChatBackendError("The model returned an empty reply.")
        return text.strip()

    @staticmethod
    def _render(conversation: Conversation) -> str:
        """The transcript as a prompt, with the model's turn left open.

        Role labels are the plainest available and carry no instruction. The
        alternative — describing the situation to the model — would be a system
        prompt by another name.
        """
        return f"{conversation.transcript()}\n\nAssistant:"


class OfflineChatBackend:
    """A stand-in that answers without a network or an API key.

    For tests and for the full dry run. Replies are derived from the participant's
    own message so a rehearsal produces a transcript with realistic shape, and
    they are deterministic so two dry runs can be compared.

    This exists rather than reusing ``agents.providers.mock``: that one is shaped
    for the Assessment Agent, returning rubric JSON and requiring a loaded rubric,
    so it cannot answer a conversational turn. :func:`build_chat_backend` picks
    between the two so the distinction never has to be remembered.
    """

    is_synthetic = True

    def __init__(self, fail_on: set[int] | None = None):
        #: Turn numbers (1-based) to fail on, for exercising the error path.
        self._fail_on = fail_on or set()

    @property
    def fingerprint(self) -> str:
        return "offline:offline"

    def reply(self, conversation: Conversation) -> str:
        turn_number = conversation.turn_count
        if turn_number in self._fail_on:
            raise ChatBackendError("[OFFLINE] simulated provider failure")

        last = conversation.participant_turns[-1].text.strip()
        return (
            f"[OFFLINE reply {turn_number}] You asked about: {last[:120]}. "
            "No model was called."
        )


def build_chat_backend(llm_config) -> ChatBackend:
    """The backend the trial's configuration calls for.

    Takes a :class:`study.trial_config.LLMConfig`. A synthetic provider yields
    :class:`OfflineChatBackend`, because the repo's mock provider answers with
    Assessment-Agent JSON and would fail every conversational turn. Anything else
    goes through the shared provider layer, whichever model that happens to be.

    Note that a dry run does *not* force the offline backend. Rehearsing against
    the real model is the point of a dress rehearsal — it is how rate limits and
    latency are discovered before they can cost a participant their forty minutes.
    """
    if llm_config.is_synthetic:
        return OfflineChatBackend()
    return ProviderChatBackend(llm_config.provider_settings())


@dataclass(frozen=True)
class UnguidedTelemetry:
    """The raw quantities the unguided-arm exclusion criterion draws on (§4.6.3)."""

    participant_id: str
    started_at: datetime
    ended_at: datetime | None
    duration: timedelta | None

    #: Messages sent by the participant.
    turn_count: int
    #: Words typed by the participant, across the session.
    word_count: int

    #: Replies the provider failed to deliver. Not an exclusion criterion —
    #: a participant is not responsible for a 429 — but a run-quality signal.
    failed_replies: int

    #: Which model actually answered, recorded per session rather than assumed
    #: from config, so a mid-run provider change cannot pass unnoticed.
    backend_fingerprint: str = ""


class UnguidedSession:
    """One participant's 40 minutes with an unconstrained chat."""

    def __init__(self, participant_id: str, backend: ChatBackend, started_at: datetime):
        self.participant_id = participant_id
        self.backend = backend
        self.conversation = Conversation(
            participant_id=participant_id, started_at=started_at
        )

    def send(self, text: str, now: datetime) -> Turn:
        """Record the participant's message and return the model's reply turn.

        A provider failure is recorded as a failed model turn rather than raised.
        The participant's message is already in the transcript by then and stays
        there — their words are the measured quantity, and dropping them because
        the network faltered would understate their engagement in exactly the
        data the exclusion criterion reads. They can simply send again.

        This mirrors the rule the tutoring loop already settled on, that a
        provider failure never costs a student one of their attempts.
        """
        if not text.strip():
            raise ValueError("An empty message is not a turn.")

        self.conversation.add(Turn(speaker=Speaker.PARTICIPANT, text=text, at=now))

        try:
            reply = self.backend.reply(self.conversation)
        except ChatBackendError as exc:
            return self.conversation.add(
                Turn(speaker=Speaker.MODEL, text="", at=now, error=str(exc))
            )

        return self.conversation.add(
            Turn(speaker=Speaker.MODEL, text=reply, at=now)
        )

    def close(self, at: datetime) -> None:
        """End the session when the intervention period does."""
        self.conversation.close(at)

    def telemetry(self) -> UnguidedTelemetry:
        conversation = self.conversation
        return UnguidedTelemetry(
            participant_id=self.participant_id,
            started_at=conversation.started_at,
            ended_at=conversation.ended_at,
            duration=conversation.duration,
            turn_count=conversation.turn_count,
            word_count=conversation.word_count,
            failed_replies=conversation.failed_replies,
            backend_fingerprint=self.backend.fingerprint,
        )
