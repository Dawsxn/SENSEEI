"""The Orchestrator's rules, tested with plain values.

No database, no agents, no event loop. This is the payoff of keeping the loop
logic pure: every branch is a table row.
"""

from __future__ import annotations

import pytest

from agents.tutor import FINAL_FAIL, FIRST_ATTEMPT, PASSED, RETRY
from backend.models import SeeiStep, SessionStatus, Verdict
from backend.orchestrator import (
    MAX_ATTEMPTS,
    Decision,
    attempts_left,
    next_step,
    opening_situation,
    resolve,
)

STATE = SeeiStep.STATE
ELABORATE = SeeiStep.ELABORATE
EXEMPLIFY = SeeiStep.EXEMPLIFY
ILLUSTRATE = SeeiStep.ILLUSTRATE
PASS = Verdict.PASS
FAIL = Verdict.FAIL


def test_the_first_message_of_a_step_is_a_prompt():
    assert opening_situation() == FIRST_ATTEMPT


@pytest.mark.parametrize(
    "step, expected",
    [
        (STATE, ELABORATE),
        (ELABORATE, EXEMPLIFY),
        (EXEMPLIFY, ILLUSTRATE),
        (ILLUSTRATE, None),
    ],
)
def test_step_advances_in_order_and_stops_at_the_last(step, expected):
    assert next_step(step) == expected


def test_attempts_left_counts_down_and_never_goes_negative():
    assert attempts_left(1) == 2
    assert attempts_left(2) == 1
    assert attempts_left(3) == 0
    assert attempts_left(4) == 0  # defensive: never below zero


def test_pass_on_a_middle_step_advances_and_opens_the_next():
    d = resolve(STATE, attempt_number=1, verdict=PASS)
    assert d.situation == PASSED
    assert d.new_status is SessionStatus.IN_PROGRESS
    assert d.new_current_step == ELABORATE
    assert d.open_next == ELABORATE  # a fresh Prompt is owed
    assert not d.fallback
    assert not d.terminal


def test_pass_on_the_last_step_completes_the_session():
    d = resolve(ILLUSTRATE, attempt_number=1, verdict=PASS)
    assert d.situation == PASSED
    assert d.new_status is SessionStatus.COMPLETE
    assert d.new_current_step == ILLUSTRATE  # nowhere to advance to
    assert d.open_next is None  # no next step to open
    assert d.terminal


def test_a_late_pass_still_advances():
    """Passing on attempt 3 is a pass, not a fallback."""
    d = resolve(ELABORATE, attempt_number=MAX_ATTEMPTS, verdict=PASS)
    assert d.situation == PASSED
    assert d.new_current_step == EXEMPLIFY


@pytest.mark.parametrize("attempt", [1, 2])
def test_fail_with_attempts_left_re_prompts_the_same_step(attempt):
    d = resolve(ELABORATE, attempt_number=attempt, verdict=FAIL)
    assert d.situation == RETRY
    assert d.new_status is SessionStatus.IN_PROGRESS
    assert d.new_current_step == ELABORATE  # stays put
    assert d.open_next is None  # the re-prompt is inside the RETRY message
    assert not d.fallback
    assert not d.terminal


def test_fail_on_the_last_attempt_falls_back_and_ends_the_session():
    d = resolve(STATE, attempt_number=MAX_ATTEMPTS, verdict=FAIL)
    assert d.situation == FINAL_FAIL
    assert d.new_status is SessionStatus.FALLBACK
    assert d.fallback  # the static copy follows the feedback
    assert d.terminal


def test_final_fail_gives_feedback_but_never_re_prompts():
    """FINAL_FAIL is RETRY minus the Re-Prompt; there is no attempt to invite."""
    d = resolve(STATE, attempt_number=MAX_ATTEMPTS, verdict=FAIL)
    assert d.situation == FINAL_FAIL
    assert d.open_next is None


def test_a_fallback_on_the_last_step_is_still_a_fallback_not_a_completion():
    d = resolve(ILLUSTRATE, attempt_number=MAX_ATTEMPTS, verdict=FAIL)
    assert d.new_status is SessionStatus.FALLBACK
    assert d.situation == FINAL_FAIL


def test_decision_is_immutable():
    d = Decision(PASSED, SessionStatus.COMPLETE, ILLUSTRATE)
    with pytest.raises(Exception):
        d.situation = RETRY  # type: ignore[misc]
