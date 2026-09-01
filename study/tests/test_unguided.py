"""The unguided-LLM arm: no scaffolding, no baked-in model, no lost words."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from study.interventions.conversation import (
    Conversation,
    ConversationClosed,
    Speaker,
    Turn,
    count_words,
)
from study.interventions.unguided import (
    NO_SYSTEM_PROMPT,
    ChatBackend,
    ChatBackendError,
    OfflineChatBackend,
    ProviderChatBackend,
    UnguidedSession,
    build_chat_backend,
)

T0 = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def session(**kwargs) -> UnguidedSession:
    return UnguidedSession("P-001", OfflineChatBackend(**kwargs), started_at=T0)


# --- no scaffolding -------------------------------------------------------


def test_there_is_no_system_prompt_at_all():
    """§4.6.2: 'no pedagogical system prompt'. Not a neutral one — none."""
    assert NO_SYSTEM_PROMPT == ""


def test_the_offline_backend_satisfies_the_protocol():
    assert isinstance(OfflineChatBackend(), ChatBackend)


# --- the model is not baked in --------------------------------------------


def test_the_backend_is_swappable_without_touching_the_session():
    """A different model, or provider, must be a config change and nothing else."""

    class Elsewhere:
        fingerprint = "somewhere:else"

        def reply(self, conversation):
            return "a reply from another provider"

    live = UnguidedSession("P-002", Elsewhere(), started_at=T0)
    live.send("hello", at(1))

    assert live.telemetry().backend_fingerprint == "somewhere:else"


def test_the_answering_model_is_recorded_per_session():
    """Recorded rather than assumed, so a mid-run change cannot pass unnoticed."""
    assert session().telemetry().backend_fingerprint == "offline:offline"


def test_the_provider_backend_builds_from_trial_settings():
    """The arm's model comes from trial.yaml, through the shared provider layer."""
    from study.trial_config import LLMConfig

    backend = ProviderChatBackend(LLMConfig(provider="mock").provider_settings())
    assert backend.fingerprint.startswith("mock:")


def test_a_synthetic_provider_yields_the_offline_backend():
    """agents' mock answers with rubric JSON and cannot hold a conversation."""
    from study.trial_config import LLMConfig

    assert isinstance(build_chat_backend(LLMConfig(provider="mock")), OfflineChatBackend)


def test_a_real_provider_goes_through_the_shared_provider_layer(monkeypatch):
    from study.trial_config import LLMConfig

    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")
    backend = build_chat_backend(LLMConfig(provider="openai_compat", model="x"))
    assert isinstance(backend, ProviderChatBackend)


def test_a_missing_api_key_fails_at_build_time(monkeypatch):
    """Better a refused pre-flight than a participant losing forty minutes."""
    from study.trial_config import LLMConfig

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Missing API key"):
        build_chat_backend(LLMConfig(provider="openai_compat", model="x"))


def test_the_chat_asks_for_prose_not_json():
    """Only the Assessment Agent needs structured output."""
    from study.trial_config import LLMConfig

    assert LLMConfig().provider_settings()["json_mode"] is False


def test_the_prompt_is_the_transcript_with_the_model_turn_left_open():
    convo = Conversation("P-001", started_at=T0)
    convo.add(Turn(Speaker.PARTICIPANT, "what is strategy?", at(1)))
    convo.add(Turn(Speaker.MODEL, "It is a plan.", at(1)))
    convo.add(Turn(Speaker.PARTICIPANT, "say more", at(2)))

    rendered = ProviderChatBackend._render(convo)

    assert rendered.endswith("Assistant:")
    assert "User: what is strategy?" in rendered
    assert "Assistant: It is a plan." in rendered


# --- the measured quantities ----------------------------------------------


def test_turns_and_words_count_only_the_participant():
    """A lazy question answered at length is not engagement (§4.6.3)."""
    live = session()
    live.send("what is a business model", at(1))
    live.send("ok thanks", at(2))

    telemetry = live.telemetry()
    assert telemetry.turn_count == 2
    assert telemetry.word_count == 7


def test_session_length_is_measured_to_the_close():
    live = session()
    live.send("hello", at(1))
    live.close(at(40))

    assert live.telemetry().duration == timedelta(minutes=40)


def test_duration_is_unknown_until_the_session_closes():
    assert session().telemetry().duration is None


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", 0),
        ("   \n\t ", 0),
        ("one", 1),
        ("two  spaced   words", 3),
        ("line\nbreaks\ncount", 3),
    ],
)
def test_word_counting_is_the_obvious_rule(text, expected):
    assert count_words(text) == expected


# --- a provider failure must not cost the participant ---------------------


def test_a_failed_reply_keeps_the_participants_words():
    """Their words are the measured quantity; a 429 must not deflate it."""
    live = session(fail_on={1})
    live.send("a question with six words here", at(1))

    telemetry = live.telemetry()
    assert telemetry.turn_count == 1
    assert telemetry.word_count == 6
    assert telemetry.failed_replies == 1


def test_a_failure_is_recorded_rather_than_raised():
    live = session(fail_on={1})
    turn = live.send("hello", at(1))

    assert turn.failed
    assert turn.speaker is Speaker.MODEL


def test_the_participant_can_simply_send_again_after_a_failure():
    live = session(fail_on={1})
    live.send("first", at(1))
    second = live.send("second", at(2))

    assert not second.failed
    assert live.telemetry().turn_count == 2


def test_a_failed_turn_is_left_out_of_the_transcript():
    """The participant never saw it, so the model must not be shown it either."""
    live = session(fail_on={1})
    live.send("first", at(1))

    assert "Assistant: " not in live.conversation.transcript()


def test_an_empty_reply_from_the_model_counts_as_a_failure():
    class Silent:
        fingerprint = "silent:silent"

        def reply(self, conversation):
            raise ChatBackendError("The model returned an empty reply.")

    live = UnguidedSession("P-003", Silent(), started_at=T0)
    assert live.send("hello", at(1)).failed


def test_an_empty_message_is_not_a_turn():
    with pytest.raises(ValueError):
        session().send("   ", at(1))


# --- the transcript -------------------------------------------------------


def test_nothing_can_be_recorded_after_the_period_ends():
    live = session()
    live.close(at(40))
    with pytest.raises(ConversationClosed):
        live.send("one more", at(41))


def test_closing_twice_keeps_the_first_end_time():
    live = session()
    live.close(at(40))
    live.close(at(45))
    assert live.conversation.ended_at == at(40)


def test_turns_must_be_recorded_in_order():
    convo = Conversation("P-001", started_at=T0)
    convo.add(Turn(Speaker.PARTICIPANT, "second", at(5)))
    with pytest.raises(ValueError, match="in order"):
        convo.add(Turn(Speaker.PARTICIPANT, "first", at(1)))


def test_the_offline_backend_is_deterministic():
    """Two dry runs must be comparable."""
    a, b = session(), session()
    a.send("what is strategy", at(1))
    b.send("what is strategy", at(1))
    assert a.conversation.transcript() == b.conversation.transcript()


def test_the_offline_backend_is_marked_synthetic():
    assert OfflineChatBackend().is_synthetic is True
