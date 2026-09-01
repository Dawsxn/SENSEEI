"""The phase engine: what a participant does, in what order, and when they move on.

Every participant walks the same sequence (Table 4.11), differing only in what
the intervention phase serves them and in whether they finish with the SUS:

    demographics -> pre-test -> intervention -> post-test A -> SBA -> [SUS] -> done

**The 40 minutes are a ceiling, not a floor.** A participant who finishes the
reading early continues straight to the post-test; nobody is held back waiting
for the rest of the room. The period's only remaining job is to stop a session
that is still running when time is up, which Section 4.6.2 anticipates ("time
expires while a stage is in progress") and which the intention-to-treat analysis
absorbs.

    Section 4.6.4 was revised to allow this. An earlier draft held early
    finishers at their station so that exposure time was constant across groups;
    that is no longer the procedure, and this engine implements the revision.

    Two consequences worth keeping in view. Time-on-task now varies between
    participants and is not controlled by design, so it is something the analysis
    accounts for rather than something the procedure has already handled — which
    is why every phase records its own duration.

    And the passive arm's exclusion criterion is live. Section 4.6.3 excludes a
    passive participant who "advances to the post-test before a realistic minimum
    reading time has elapsed", which could never fire while everyone was held for
    the full period.

Two rules follow from the data this produces being evidence:

1. **Time is measured server-side.** A client clock can be wrong, or changed.
2. **State transitions are explicit and recorded.** Every visit to a phase keeps
   its entry and exit time, so per-phase durations are a property of the record
   rather than something reconstructed later. Those durations are what the
   exclusion criteria of Section 4.6.3 are computed from; see ``exclusion.py``.
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

    #: The assigned instructional mode. Up to 40 minutes, same text for all arms.
    INTERVENTION = "intervention"

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

    @property
    def label(self) -> str:
        return self.value.replace("_", " ")


#: The 40 minutes of Table 4.11, now the longest a participant may spend rather
#: than the time they must spend. Lives here so changing it is a one-line edit.
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

    #: True when the intervention was ended by the clock rather than by the
    #: participant. Distinguishes someone who ran out of time from someone who
    #: finished, which the two look identical without it.
    expired: bool = False

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
    #: When the intervention clock started, for the deadline.
    intervention_started_at: datetime | None = None
    history: tuple[PhaseVisit, ...] = field(default_factory=tuple)


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
    """The phase that follows, or None if there is nowhere left to go."""
    if phase is Phase.SBA:
        return Phase.SUS if arm.takes_sus else Phase.DONE

    chain = {
        Phase.DEMOGRAPHICS: Phase.PRE_TEST,
        Phase.PRE_TEST: Phase.INTERVENTION,
        Phase.INTERVENTION: Phase.POST_TEST_A,
        Phase.POST_TEST_A: Phase.SBA,
        Phase.SUS: Phase.DONE,
        Phase.DONE: None,
    }
    return chain[phase]


def deadline(
    state: ParticipantState, timing: TrialTiming | None = None
) -> datetime | None:
    """When this participant's intervention must end, or None outside it."""
    if state.phase is not Phase.INTERVENTION or state.intervention_started_at is None:
        return None
    timing = timing or TrialTiming()
    return state.intervention_started_at + timedelta(seconds=timing.intervention_seconds)


def seconds_remaining(
    state: ParticipantState,
    now: datetime,
    timing: TrialTiming | None = None,
) -> int:
    """Seconds left on the intervention, never negative. 0 outside it."""
    ends_at = deadline(state, timing)
    if ends_at is None:
        return 0
    return max(0, int(round((ends_at - now).total_seconds())))


def is_expired(
    state: ParticipantState,
    now: datetime,
    timing: TrialTiming | None = None,
) -> bool:
    """Whether the intervention period has run out for this participant."""
    ends_at = deadline(state, timing)
    return ends_at is not None and now >= ends_at


def advance(
    state: ParticipantState,
    now: datetime,
    timing: TrialTiming | None = None,
) -> ParticipantState:
    """Move to the next phase.

    Always permitted while the session is running. A participant who finishes the
    reading in twenty minutes goes straight on to the post-test; the period is a
    ceiling, not a wait.
    """
    target = next_phase(state.phase, state.arm)
    if target is None:
        raise PhaseError("The session is already complete.")

    expired = state.phase is Phase.INTERVENTION and is_expired(state, now, timing)
    return _move(state, target, now, expired=expired)


def _move(
    state: ParticipantState,
    target: Phase,
    now: datetime,
    expired: bool = False,
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
        expired=expired,
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
    """Time spent in each completed phase.

    The raw per-phase timing the exclusion analysis draws on (§4.6.3). The
    current, still-open phase is excluded: it has no duration yet.
    """
    totals: dict[Phase, timedelta] = {}
    for visit in state.history:
        if visit.duration is None:
            continue
        totals[visit.phase] = totals.get(visit.phase, timedelta()) + visit.duration
    return totals


def time_in_phase(state: ParticipantState, phase: Phase, now: datetime) -> timedelta:
    """Time in a phase, counting the current visit if they are still in it."""
    total = phase_durations(state).get(phase, timedelta())
    if state.phase is phase:
        total += max(now - state.entered_at, timedelta())
    return total


def ran_out_of_time(state: ParticipantState) -> bool:
    """Whether the clock ended their intervention rather than they did.

    Not an exclusion criterion — running out of time is engagement, not the
    absence of it — but it separates a participant cut off mid-step from one who
    chose to move on, which the durations alone cannot.
    """
    return any(visit.expired for visit in state.history)


def utcnow() -> datetime:
    """Current time, timezone-aware. The single source of 'now' for the harness."""
    return datetime.now(timezone.utc)


class PhaseError(RuntimeError):
    """An impossible transition was requested."""
