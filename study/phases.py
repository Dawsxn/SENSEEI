"""The phase engine: what a participant does, in what order, and when they may move on.

Every participant walks the same sequence (Table 4.11), differing only in what
the intervention phase serves them and in whether they finish with the SUS:

    demographics -> pre-test -> intervention -> post-test A -> SBA -> [SUS] -> done

The engine exists for one reason above all others: **exposure time must be held
constant across the three arms.** Section 4.6.4 gives every participant the same
40 minutes with the reading, and says that a participant who finishes the SEE-I
sequence early "remain[s] at their station until the period ends". If a fast
SENSEE-I participant could start the post-test at minute 25 while a passive-arm
participant read for the full 40, the arms would differ in time-on-task as well
as in instructional mode, and the study's independent variable would no longer be
the one it claims to be.

So the gate out of the intervention is time, not completion. A participant who
finishes early moves to HOLD and waits; a participant still working at 40:00 is
cut off mid-step, which Section 4.6.2 explicitly anticipates ("time expires while
a stage is in progress") and which the intention-to-treat analysis is built to
absorb.

The engine owns that clock itself rather than asking the SENSEE-I application to
enforce it. That keeps the harness free of any dependency on the app's internals,
and means the same gate governs all three arms identically.

Two rules follow from the data this produces being evidence:

1. **Time is measured server-side.** A client clock can be wrong, or changed.
2. **State transitions are explicit and recorded.** Every visit to a phase keeps
   its entry and exit time, so per-phase durations are a property of the record
   rather than something reconstructed later.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum

from .arms import Arm


class Phase(str, Enum):
    """One step of the session sequence."""

    #: Year level, college affiliation, and the eligibility attributes (§4.6.6).
    DEMOGRAPHICS = "demographics"

    #: Likert familiarity ratings and factual items, establishing baseline
    #: equivalence across arms (§4.6.4).
    PRE_TEST = "pre_test"

    #: The assigned instructional mode. 40 minutes, same text for all arms.
    INTERVENTION = "intervention"

    #: Finished the intervention early and waiting out the remaining time, so
    #: exposure is equal across arms (§4.6.4).
    HOLD = "hold"

    #: Multiple-choice, paired to the pre-test.
    POST_TEST_A = "post_test_a"

    #: The Scenario-Based Assessment: the study's primary outcome measure.
    SBA = "sba"

    #: System Usability Scale. SENSEE-I arm only.
    SUS = "sus"

    DONE = "done"

    @property
    def is_terminal(self) -> bool:
        return self is Phase.DONE


#: The 40 minutes of Table 4.11. Provisional in the sense that the pilot runs on
#: the same code and may use a shorter value; it lives here so changing it is a
#: one-line edit rather than a search.
DEFAULT_INTERVENTION_SECONDS = 40 * 60


@dataclass(frozen=True)
class TrialTiming:
    """Timing rules for a trial run. Recorded alongside the data it governs."""

    intervention_seconds: int = DEFAULT_INTERVENTION_SECONDS

    def __post_init__(self) -> None:
        if self.intervention_seconds <= 0:
            raise ValueError(
                f"Intervention must last a positive time, got {self.intervention_seconds}s"
            )


@dataclass(frozen=True)
class PhaseVisit:
    """One stay in one phase. Closed when the participant leaves it."""

    phase: Phase
    entered_at: datetime
    left_at: datetime | None = None
    #: True when a proctor released this phase before its gate opened. Breaks
    #: the equal-exposure guarantee, so it is recorded rather than hidden.
    forced: bool = False

    @property
    def duration(self) -> timedelta | None:
        if self.left_at is None:
            return None
        return self.left_at - self.entered_at


@dataclass(frozen=True)
class ParticipantState:
    """Where one participant is in the sequence, and how they got there."""

    participant_id: str
    arm: Arm
    phase: Phase
    entered_at: datetime
    #: When the intervention clock started. The gate is measured from here, and
    #: it keeps running through HOLD.
    intervention_started_at: datetime | None = None
    history: tuple[PhaseVisit, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Gate:
    """Whether a participant may leave their current phase, and why not if not."""

    allowed: bool
    reason: str = ""
    seconds_remaining: int = 0


def start(participant_id: str, arm: Arm, now: datetime) -> ParticipantState:
    """Begin a participant's session at the first phase.

    Consent is not a phase here. It is collected on paper before check-in
    (§4.6.4: the participant keeps one signed copy, the researchers retain the
    second), and the harness records only that it was given.
    """
    return ParticipantState(
        participant_id=participant_id,
        arm=arm,
        phase=Phase.DEMOGRAPHICS,
        entered_at=now,
    )


def next_phase(phase: Phase, arm: Arm) -> Phase | None:
    """The phase that follows, or None if there is nowhere left to go.

    HOLD is not in this chain. It is a detour off the intervention, entered by
    :func:`hold`, and it leads to the same place the intervention does.
    """
    if phase in (Phase.INTERVENTION, Phase.HOLD):
        return Phase.POST_TEST_A
    if phase is Phase.SBA:
        return Phase.SUS if arm.takes_sus else Phase.DONE

    chain = {
        Phase.DEMOGRAPHICS: Phase.PRE_TEST,
        Phase.PRE_TEST: Phase.INTERVENTION,
        Phase.POST_TEST_A: Phase.SBA,
        Phase.SUS: Phase.DONE,
        Phase.DONE: None,
    }
    return chain[phase]


def seconds_remaining(
    state: ParticipantState,
    now: datetime,
    timing: TrialTiming | None = None,
) -> int:
    """Seconds still owed on the intervention clock, or 0 outside it."""
    return check_gate(state, now, timing).seconds_remaining


def check_gate(
    state: ParticipantState,
    now: datetime,
    timing: TrialTiming | None = None,
) -> Gate:
    """Whether ``state`` may advance right now.

    Only one phase is gated. Everything else advances when the participant
    submits, because the other durations in Table 4.11 are allowances rather
    than requirements: someone who finishes the MCQ in six minutes has finished
    it, whereas someone who finishes the intervention in twenty-five has had
    less exposure to the material than their peers.
    """
    timing = timing or TrialTiming()

    if state.phase.is_terminal:
        return Gate(allowed=False, reason="The session is already complete.")

    if state.phase not in (Phase.INTERVENTION, Phase.HOLD):
        return Gate(allowed=True)

    if state.intervention_started_at is None:
        # Only reachable if a state was assembled by hand rather than by the
        # engine. Refuse rather than treat a missing clock as an expired one.
        return Gate(
            allowed=False,
            reason="The intervention clock was never started.",
        )

    elapsed = (now - state.intervention_started_at).total_seconds()
    remaining = int(round(timing.intervention_seconds - elapsed))
    if remaining > 0:
        minutes, seconds = divmod(remaining, 60)
        return Gate(
            allowed=False,
            reason=(
                f"The intervention period has {minutes}m {seconds:02d}s left. "
                "Exposure time is held equal across all three groups."
            ),
            seconds_remaining=remaining,
        )
    return Gate(allowed=True)


def hold(state: ParticipantState, now: datetime) -> ParticipantState:
    """Move a participant who has finished the intervention early into HOLD.

    Always permitted: it does not shorten their exposure, it only records that
    they stopped working before the period ended. Time spent held is itself
    signal — a SENSEE-I participant who finished at minute twelve is a different
    case from one who was still going at thirty-nine.
    """
    if state.phase is not Phase.INTERVENTION:
        raise PhaseError(
            f"Only an in-progress intervention can be held, not {state.phase.value}."
        )
    return _move(state, Phase.HOLD, now, forced=False)


def advance(
    state: ParticipantState,
    now: datetime,
    timing: TrialTiming | None = None,
    force: bool = False,
) -> ParticipantState:
    """Move to the next phase, refusing if the gate is closed.

    ``force`` is the proctor's override, for technical incidents where holding
    someone at their station is not the right call. It is recorded on the visit
    it releases, because a forced release means that participant did not get the
    same exposure as everyone else and the analysis needs to be able to see that.
    """
    gate = check_gate(state, now, timing)
    if not gate.allowed and not force:
        raise PhaseGateError(gate.reason, seconds_remaining=gate.seconds_remaining)

    target = next_phase(state.phase, state.arm)
    if target is None:
        raise PhaseError("The session is already complete.")

    return _move(state, target, now, forced=force and not gate.allowed)


def _move(
    state: ParticipantState,
    target: Phase,
    now: datetime,
    forced: bool,
) -> ParticipantState:
    """Close the current visit, open the next. The only writer of phase history."""
    if now < state.entered_at:
        raise PhaseError(
            "Refusing to record a transition that moves backwards in time "
            f"({now.isoformat()} precedes {state.entered_at.isoformat()})."
        )

    closed = PhaseVisit(
        phase=state.phase,
        entered_at=state.entered_at,
        left_at=now,
        forced=forced,
    )
    started = state.intervention_started_at
    if target is Phase.INTERVENTION and started is None:
        started = now

    return replace(
        state,
        phase=target,
        entered_at=now,
        intervention_started_at=started,
        history=state.history + (closed,),
    )


def phase_durations(state: ParticipantState) -> dict[Phase, timedelta]:
    """Time spent in each completed phase, summed over repeat visits.

    This is the per-phase timing the exclusion analysis draws on (§4.6.3). The
    current, still-open phase is excluded: it has no duration yet.
    """
    totals: dict[Phase, timedelta] = {}
    for visit in state.history:
        if visit.duration is None:
            continue
        totals[visit.phase] = totals.get(visit.phase, timedelta()) + visit.duration
    return totals


def was_forced(state: ParticipantState) -> bool:
    """Whether a proctor ever released this participant past a closed gate."""
    return any(visit.forced for visit in state.history)


def utcnow() -> datetime:
    """Current time, timezone-aware. The single source of 'now' for the harness."""
    return datetime.now(timezone.utc)


class PhaseError(RuntimeError):
    """An impossible transition was requested."""


class PhaseGateError(PhaseError):
    """The transition is legal but not yet permitted."""

    def __init__(self, reason: str, seconds_remaining: int = 0):
        super().__init__(reason)
        self.seconds_remaining = seconds_remaining
