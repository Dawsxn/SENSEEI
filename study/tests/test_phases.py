"""The phase engine, and the intervention deadline.

The 40 minutes are a ceiling, not a floor: a participant who finishes early goes
straight on, and the clock exists only to stop a session still running when time
is up. These tests hold both halves of that — that nobody is blocked from moving
on, and that nobody keeps working past the deadline.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from study.arms import Arm
from study.phases import (
    DEFAULT_INTERVENTION_SECONDS,
    Phase,
    PhaseError,
    TrialTiming,
    advance,
    deadline,
    is_expired,
    next_phase,
    phase_durations,
    ran_out_of_time,
    seconds_remaining,
    start,
    time_in_phase,
)

T0 = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def reach_intervention(arm: Arm = Arm.SENSEEI):
    """Walk a participant to the start of their intervention, at minute 8."""
    state = start("P-001", arm, T0)
    state = advance(state, at(3))   # demographics -> pre-test
    state = advance(state, at(8))   # pre-test -> intervention
    return state


# --- the sequence ---------------------------------------------------------


def test_sequence_for_the_senseei_arm_ends_with_the_sus():
    assert next_phase(Phase.SBA, Arm.SENSEEI) is Phase.SUS
    assert next_phase(Phase.SUS, Arm.SENSEEI) is Phase.DONE


@pytest.mark.parametrize("arm", [Arm.UNGUIDED_LLM, Arm.PASSIVE])
def test_control_arms_skip_the_sus(arm):
    """There is no platform for a control participant to rate (Table 4.11)."""
    assert next_phase(Phase.SBA, arm) is Phase.DONE


def test_the_intervention_leads_to_the_post_test():
    assert next_phase(Phase.INTERVENTION, Arm.SENSEEI) is Phase.POST_TEST_A


def test_a_session_starts_at_demographics_not_consent():
    """Consent is collected on paper before check-in (§4.6.4)."""
    assert start("P-001", Arm.PASSIVE, T0).phase is Phase.DEMOGRAPHICS


def test_full_walk_through_reaches_done():
    state = reach_intervention(Arm.SENSEEI)
    state = advance(state, at(30))  # intervention -> post-test A
    state = advance(state, at(40))  # -> SBA
    state = advance(state, at(58))  # -> SUS
    state = advance(state, at(62))  # -> done
    assert state.phase.is_terminal


# --- finishing early ------------------------------------------------------


def test_a_participant_who_finishes_early_moves_straight_on():
    """Nobody waits for the room."""
    state = advance(reach_intervention(), at(8 + 12))
    assert state.phase is Phase.POST_TEST_A


@pytest.mark.parametrize("minutes", [1, 5, 20, 39])
def test_moving_on_is_allowed_at_any_point(minutes):
    state = advance(reach_intervention(), at(8 + minutes))
    assert state.phase is Phase.POST_TEST_A


def test_every_arm_may_finish_early(arm=None):
    for arm in (Arm.SENSEEI, Arm.UNGUIDED_LLM, Arm.PASSIVE):
        state = advance(reach_intervention(arm), at(8 + 10))
        assert state.phase is Phase.POST_TEST_A


def test_finishing_early_is_not_marked_as_timed_out():
    """Choosing to move on and being cut off are different facts."""
    state = advance(reach_intervention(), at(8 + 12))
    assert not ran_out_of_time(state)


# --- the deadline ---------------------------------------------------------


def test_the_deadline_is_forty_minutes_after_the_intervention_starts():
    state = reach_intervention()
    assert deadline(state) == state.intervention_started_at + timedelta(
        seconds=DEFAULT_INTERVENTION_SECONDS
    )


def test_there_is_no_deadline_outside_the_intervention():
    assert deadline(start("P-001", Arm.SENSEEI, T0)) is None


def test_the_period_expires_exactly_at_forty_minutes():
    state = reach_intervention()
    ends_at = deadline(state)

    assert not is_expired(state, ends_at - timedelta(seconds=1))
    assert is_expired(state, ends_at)


def test_advancing_after_the_deadline_is_recorded_as_timed_out():
    state = advance(reach_intervention(), at(8 + 41))
    assert ran_out_of_time(state)


def test_time_remaining_counts_down_and_stops_at_zero():
    state = reach_intervention()
    assert seconds_remaining(state, at(8 + 10)) == 30 * 60
    assert seconds_remaining(state, at(8 + 40)) == 0
    assert seconds_remaining(state, at(8 + 90)) == 0


def test_no_time_remains_outside_the_intervention():
    assert seconds_remaining(start("P-001", Arm.SENSEEI, T0), at(1)) == 0


def test_a_pilot_can_shorten_the_period():
    timing = TrialTiming(intervention_seconds=10 * 60)
    state = reach_intervention()

    assert seconds_remaining(state, at(8 + 4), timing) == 6 * 60
    assert is_expired(state, at(8 + 10), timing)


def test_a_missing_clock_never_expires():
    """A hand-assembled state must not read as out of time."""
    state = reach_intervention()
    broken = type(state)(
        participant_id=state.participant_id,
        arm=state.arm,
        phase=Phase.INTERVENTION,
        entered_at=state.entered_at,
        intervention_started_at=None,
    )
    assert not is_expired(broken, at(999))


# --- history and timing ---------------------------------------------------


def test_phase_durations_come_from_the_record():
    state = reach_intervention()
    state = advance(state, at(33))
    durations = phase_durations(state)

    assert durations[Phase.DEMOGRAPHICS] == timedelta(minutes=3)
    assert durations[Phase.PRE_TEST] == timedelta(minutes=5)
    assert durations[Phase.INTERVENTION] == timedelta(minutes=25)


def test_the_open_phase_has_no_duration_yet():
    assert Phase.INTERVENTION not in phase_durations(reach_intervention())


def test_time_in_phase_counts_the_visit_still_in_progress():
    """The passive arm's criterion is read while the participant is still there."""
    state = reach_intervention()
    assert time_in_phase(state, Phase.INTERVENTION, at(8 + 14)) == timedelta(minutes=14)


def test_time_in_phase_of_a_finished_phase_is_its_duration():
    state = advance(reach_intervention(), at(8 + 14))
    assert time_in_phase(state, Phase.INTERVENTION, at(99)) == timedelta(minutes=14)


def test_time_never_runs_backwards():
    state = reach_intervention()
    with pytest.raises(PhaseError, match="backwards in time"):
        advance(state, at(2))


def test_a_finished_session_cannot_advance_further():
    state = reach_intervention(Arm.PASSIVE)
    state = advance(state, at(20))
    state = advance(state, at(30))
    state = advance(state, at(50))  # passive arm: SBA -> done
    with pytest.raises(PhaseError):
        advance(state, at(60))


def test_state_is_immutable_across_a_transition():
    state = reach_intervention()
    advance(state, at(20))
    assert state.phase is Phase.INTERVENTION
