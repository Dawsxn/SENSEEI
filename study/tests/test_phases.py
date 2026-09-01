"""The phase engine, and above all the 40-minute gate.

If the gate leaks, the arms differ in time-on-task as well as instructional mode
and the study measures something other than what it claims to. These tests are
the guarantee that it does not.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from study.arms import Arm
from study.phases import (
    DEFAULT_INTERVENTION_SECONDS,
    Phase,
    PhaseError,
    PhaseGateError,
    TrialTiming,
    advance,
    check_gate,
    hold,
    next_phase,
    phase_durations,
    seconds_remaining,
    start,
    was_forced,
)

T0 = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def reach_intervention(arm: Arm = Arm.SENSEEI):
    """Walk a participant to the start of their intervention at T0."""
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


def test_hold_and_intervention_lead_to_the_same_place():
    for phase in (Phase.INTERVENTION, Phase.HOLD):
        assert next_phase(phase, Arm.SENSEEI) is Phase.POST_TEST_A


def test_a_session_starts_at_demographics_not_consent():
    """Consent is collected on paper before check-in (§4.6.4)."""
    assert start("P-001", Arm.PASSIVE, T0).phase is Phase.DEMOGRAPHICS


def test_full_walk_through_reaches_done():
    state = reach_intervention(Arm.SENSEEI)
    state = advance(state, at(48))  # intervention -> post-test A, gate open
    state = advance(state, at(56))  # -> SBA
    state = advance(state, at(74))  # -> SUS
    state = advance(state, at(78))  # -> done
    assert state.phase.is_terminal


# --- the gate -------------------------------------------------------------


def test_cannot_leave_the_intervention_early():
    state = reach_intervention()
    with pytest.raises(PhaseGateError):
        advance(state, at(8 + 25))


def test_cannot_leave_the_hold_early_either():
    """Finishing SEE-I at minute twelve must not buy an early post-test."""
    state = hold(reach_intervention(), at(20))
    with pytest.raises(PhaseGateError):
        advance(state, at(30))


def test_the_gate_opens_exactly_at_forty_minutes():
    state = reach_intervention()
    opens = state.intervention_started_at + timedelta(
        seconds=DEFAULT_INTERVENTION_SECONDS
    )

    assert not check_gate(state, opens - timedelta(seconds=1)).allowed
    assert check_gate(state, opens).allowed


def test_the_hold_does_not_pause_the_clock():
    """Time in HOLD counts: the point is equal exposure, not equal effort."""
    state = reach_intervention()
    held = hold(state, at(20))
    assert held.intervention_started_at == state.intervention_started_at
    assert check_gate(held, at(48)).allowed


def test_gate_reports_the_time_still_owed():
    state = reach_intervention()
    gate = check_gate(state, at(8 + 30))
    assert gate.seconds_remaining == 10 * 60
    assert "10m 00s" in gate.reason


def test_the_gate_applies_to_every_arm_identically():
    for arm in (Arm.SENSEEI, Arm.UNGUIDED_LLM, Arm.PASSIVE):
        state = reach_intervention(arm)
        with pytest.raises(PhaseGateError):
            advance(state, at(8 + 39))


def test_no_other_phase_is_gated():
    """The other durations in Table 4.11 are allowances, not requirements."""
    state = start("P-001", Arm.SENSEEI, T0)
    assert check_gate(state, at(0.5)).allowed


def test_a_pilot_can_shorten_the_intervention():
    timing = TrialTiming(intervention_seconds=10 * 60)
    state = reach_intervention()
    assert check_gate(state, at(8 + 10), timing).allowed
    assert seconds_remaining(state, at(8 + 4), timing) == 6 * 60


def test_a_missing_clock_is_refused_rather_than_treated_as_expired():
    """A hand-assembled state must not fall open."""
    state = reach_intervention()
    broken = type(state)(
        participant_id=state.participant_id,
        arm=state.arm,
        phase=Phase.INTERVENTION,
        entered_at=state.entered_at,
        intervention_started_at=None,
    )
    assert not check_gate(broken, at(999)).allowed


# --- the proctor override -------------------------------------------------


def test_a_proctor_can_release_someone_early():
    state = reach_intervention()
    released = advance(state, at(8 + 20), force=True)
    assert released.phase is Phase.POST_TEST_A


def test_a_forced_release_is_recorded():
    """It breaks equal exposure, so the analysis has to be able to see it."""
    state = advance(reach_intervention(), at(8 + 20), force=True)
    assert was_forced(state)


def test_forcing_an_open_gate_is_not_recorded_as_forced():
    state = advance(reach_intervention(), at(48), force=True)
    assert not was_forced(state)


def test_an_ordinary_run_is_never_flagged():
    state = advance(reach_intervention(), at(48))
    assert not was_forced(state)


# --- history and timing ---------------------------------------------------


def test_phase_durations_come_from_the_record():
    state = reach_intervention()
    state = advance(state, at(48))
    durations = phase_durations(state)

    assert durations[Phase.DEMOGRAPHICS] == timedelta(minutes=3)
    assert durations[Phase.PRE_TEST] == timedelta(minutes=5)
    assert durations[Phase.INTERVENTION] == timedelta(minutes=40)


def test_the_open_phase_has_no_duration_yet():
    state = reach_intervention()
    assert Phase.INTERVENTION not in phase_durations(state)


def test_a_hold_is_timed_separately_from_the_work():
    """Finishing at twelve and finishing at thirty-nine are different cases."""
    state = hold(reach_intervention(), at(8 + 12))
    state = advance(state, at(48))
    durations = phase_durations(state)

    assert durations[Phase.INTERVENTION] == timedelta(minutes=12)
    assert durations[Phase.HOLD] == timedelta(minutes=28)


def test_time_never_runs_backwards():
    state = reach_intervention()
    with pytest.raises(PhaseError, match="backwards in time"):
        advance(state, at(2), force=True)


def test_only_an_intervention_can_be_held():
    state = start("P-001", Arm.SENSEEI, T0)
    with pytest.raises(PhaseError):
        hold(state, at(1))


def test_a_finished_session_cannot_advance_further():
    state = reach_intervention(Arm.PASSIVE)
    state = advance(state, at(48))
    state = advance(state, at(56))
    state = advance(state, at(74))  # passive arm: SBA -> done
    with pytest.raises(PhaseError):
        advance(state, at(80))


def test_state_is_immutable_across_a_transition():
    state = reach_intervention()
    advance(state, at(48))
    assert state.phase is Phase.INTERVENTION
