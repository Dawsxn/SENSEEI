"""The §4.6.3 exclusion measures: the right quantity per arm, and no thresholds."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from study.arms import Arm
from study.exclusion import (
    EngagementRecord,
    Measure,
    build_engagement_record,
    median_of,
    summarise,
)
from study.interventions.passive import PassiveSession
from study.interventions.unguided import OfflineChatBackend, UnguidedSession
from study.phases import Phase, advance, start
from study.senseei_link import FakeSenseeiLink

T0 = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


class FakeParticipant:
    """Enough of a store Participant to build a record from."""

    def __init__(self, arm: Arm, participant_id="P-001"):
        self.participant_id = participant_id
        self.arm = arm
        state = start(participant_id, arm, T0)
        state = advance(state, at(3))
        self.state = advance(state, at(8))  # now in the intervention
        self.unguided = None
        self.passive = None
        self.responses = {}
        self.incidents = []
        self.unavailable = ""


# --- the SENSEE-I arm -----------------------------------------------------


def test_senseei_measures_session_time_and_turns():
    """§4.6.3: total session time or number of conversational turns."""
    record = build_engagement_record(
        FakeParticipant(Arm.SENSEEI), at(20), FakeSenseeiLink()
    )
    assert [m.key for m in record.measures] == ["session_seconds", "turn_count"]
    assert all(m.value is not None for m in record.measures)


def test_senseei_measures_come_from_the_application():
    """That session happened in the app, so the numbers must come from there."""
    link = FakeSenseeiLink()
    telemetry = link.fetch_telemetry("P-001")
    record = build_engagement_record(FakeParticipant(Arm.SENSEEI), at(20), link)

    turns = next(m for m in record.measures if m.key == "turn_count")
    assert turns.value == telemetry.turn_count


def test_a_participant_who_never_opened_senseei_reads_as_unknown():
    """Not starting and starting-then-stopping are different facts."""
    link = FakeSenseeiLink()
    link.delete_participant_data("P-001")

    record = build_engagement_record(FakeParticipant(Arm.SENSEEI), at(20), link)
    assert all(m.value is None for m in record.measures)


def test_unknown_is_not_reported_as_zero():
    assert Measure("k", "l", None).display == "—"
    assert not Measure("k", "l", None).is_zero


# --- the unguided arm -----------------------------------------------------


def test_unguided_measures_session_length_and_words_typed():
    """§4.6.3: session length or total word input."""
    participant = FakeParticipant(Arm.UNGUIDED_LLM)
    session = UnguidedSession("P-001", OfflineChatBackend(), started_at=at(8))
    session.send("what makes a switching cost different from a price", at(10))
    session.close(at(30))
    participant.unguided = session

    record = build_engagement_record(participant, at(30))
    words = next(m for m in record.measures if m.key == "word_count")
    seconds = next(m for m in record.measures if m.key == "session_seconds")

    assert words.value == 9
    assert seconds.value == 22 * 60


def test_unguided_words_exclude_the_model_output():
    """One lazy question answered at length is the pattern this arm can show."""
    participant = FakeParticipant(Arm.UNGUIDED_LLM)
    session = UnguidedSession("P-001", OfflineChatBackend(), started_at=at(8))
    session.send("explain everything", at(10))
    session.close(at(30))
    participant.unguided = session

    record = build_engagement_record(participant, at(30))
    words = next(m for m in record.measures if m.key == "word_count")
    assert words.value == 2


def test_session_length_is_reported_while_still_running():
    """A proctor needs the number during the run, not only once it closes."""
    participant = FakeParticipant(Arm.UNGUIDED_LLM)
    participant.unguided = UnguidedSession(
        "P-001", OfflineChatBackend(), started_at=at(8)
    )

    record = build_engagement_record(participant, at(8 + 15))
    seconds = next(m for m in record.measures if m.key == "session_seconds")

    assert seconds.value == 15 * 60


def test_a_tool_that_failed_to_start_is_not_read_as_disengagement():
    """A broken tool wearing the costume of an idle participant is the one
    confusion this record exists to prevent."""
    participant = FakeParticipant(Arm.UNGUIDED_LLM)
    participant.unavailable = "The assistant is not configured on this server."

    record = build_engagement_record(participant, at(20))

    assert record.unavailable
    assert record.needs_a_look
    assert all(m.value is None for m in record.measures)


def test_a_zero_measure_is_flagged_for_a_look():
    """Zero turns twenty minutes in usually means a broken connection."""
    participant = FakeParticipant(Arm.UNGUIDED_LLM)
    participant.unguided = UnguidedSession(
        "P-001", OfflineChatBackend(), started_at=at(8)
    )

    record = build_engagement_record(participant, at(28))
    assert record.needs_a_look


# --- the passive arm ------------------------------------------------------


def test_passive_measures_time_before_the_post_test():
    """§4.6.3: advancing to the post-test before a minimum reading time.

    Live only because participants may now leave early; while everyone was held
    for the full period this could never fire.
    """
    participant = FakeParticipant(Arm.PASSIVE)
    participant.passive = PassiveSession("P-001", started_at=at(8))

    record = build_engagement_record(participant, at(8 + 6))
    before = next(m for m in record.measures if m.key == "intervention_seconds")

    assert before.value == 6 * 60


def test_passive_reports_time_on_text_alongside_phase_duration():
    """Phase duration cannot tell whether the text was open."""
    participant = FakeParticipant(Arm.PASSIVE)
    session = PassiveSession("P-001", started_at=at(8))
    session.went_away(at(14))
    participant.passive = session

    record = build_engagement_record(participant, at(38))
    phase = next(m for m in record.measures if m.key == "intervention_seconds")
    on_text = next(m for m in record.measures if m.key == "time_on_text_seconds")

    assert phase.value == 30 * 60
    assert on_text.value == 6 * 60


def test_passive_reports_scroll_depth():
    participant = FakeParticipant(Arm.PASSIVE)
    session = PassiveSession("P-001", started_at=at(8))
    session.scrolled(0.4, at(12))
    participant.passive = session

    record = build_engagement_record(participant, at(20))
    depth = next(m for m in record.measures if m.key == "max_scroll_depth")

    assert depth.value == pytest.approx(0.4)
    assert depth.display == "40%"


# --- attention checks -----------------------------------------------------


def test_a_failed_attention_check_is_recorded():
    """§4.6.3: failing one excludes automatically. Recorded, not enforced here."""
    participant = FakeParticipant(Arm.PASSIVE)
    participant.responses = {
        Phase.PRE_TEST: {"attention_answered": 1, "attention_failed": 1},
        Phase.POST_TEST_A: {"attention_answered": 1, "attention_failed": 0},
    }

    record = build_engagement_record(participant, at(20))
    assert record.failed_attention_check
    assert record.attention_display == "1/2"


def test_attention_checks_read_as_unknown_before_the_instruments_exist():
    record = build_engagement_record(FakeParticipant(Arm.PASSIVE), at(20))
    assert not record.failed_attention_check
    assert record.attention_display == "—"


# --- no thresholds --------------------------------------------------------


def test_no_threshold_is_stored_anywhere_in_the_module():
    """§4.6.3 derives the cutoffs from the pilot; hard-coding one would fix them."""
    import inspect

    import study.exclusion as module

    source = inspect.getsource(module)
    for word in ("THRESHOLD", "MINIMUM_", "CUTOFF"):
        assert word not in source


def test_a_record_never_says_a_participant_is_excluded():
    record = build_engagement_record(FakeParticipant(Arm.PASSIVE), at(20))
    assert not hasattr(record, "excluded")
    assert not hasattr(record, "is_excluded")


# --- reporting ------------------------------------------------------------


def test_a_record_flattens_for_export():
    participant = FakeParticipant(Arm.UNGUIDED_LLM)
    participant.unguided = UnguidedSession(
        "P-001", OfflineChatBackend(), started_at=at(8)
    )
    row = build_engagement_record(participant, at(20)).as_row()

    assert row["participant_id"] == "P-001"
    assert row["arm"] == "unguided_llm"
    assert "word_count" in row


def test_medians_describe_the_distribution():
    records = [
        EngagementRecord("P-001", Arm.UNGUIDED_LLM, (Measure("word_count", "w", 10),)),
        EngagementRecord("P-002", Arm.UNGUIDED_LLM, (Measure("word_count", "w", 30),)),
        EngagementRecord("P-003", Arm.UNGUIDED_LLM, (Measure("word_count", "w", 50),)),
    ]
    assert median_of(records, "word_count") == 30


def test_medians_ignore_participants_without_the_measure():
    records = [
        EngagementRecord("P-001", Arm.UNGUIDED_LLM, (Measure("word_count", "w", 10),)),
        EngagementRecord("P-002", Arm.UNGUIDED_LLM, (Measure("word_count", "w", None),)),
    ]
    assert median_of(records, "word_count") == 10


def test_a_median_of_nothing_is_unknown():
    assert median_of([], "word_count") is None


def test_the_summary_counts_what_a_proctor_watches():
    records = [
        EngagementRecord("P-001", Arm.PASSIVE, (Measure("k", "l", 0),)),
        EngagementRecord("P-002", Arm.PASSIVE, (Measure("k", "l", 5),),
                         attention_failed=1, attention_answered=2),
    ]
    summary = summarise(records)

    assert summary["participants"] == 2
    assert summary["needing_a_look"] == 1
    assert summary["failed_attention"] == 1


def test_durations_display_as_minutes_and_seconds():
    assert Measure("k", "l", 90, "min").display == "1:30"
