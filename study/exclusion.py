"""The quantities Section 4.6.3 excludes participants on, gathered in one place.

The manuscript defines a different criterion per arm, plus one that applies to
everybody:

| Arm | Excluded if... |
| --- | --- |
| SENSEE-I | total session time **or** number of conversational turns falls below a minimum threshold |
| Unguided LLM | session length **or** total word input falls below a minimum threshold |
| Passive control | they advance to the post-test before a realistic minimum reading time has elapsed |
| All | they fail an attention check embedded in the surveys |

**No threshold is applied here, and none belongs in this codebase.** Section
4.6.3 is explicit that "the exact numerical cutoffs for each threshold will be
empirically derived prior to the main data collection phase" — that is, from the
pilot. A cutoff compiled into the tool could not then be revised without
invalidating everything collected under the old one, and the decision to exclude
a participant would become a deployment artefact rather than an analytical one.
So this module reports numbers. Someone else decides what they mean.

The attention-check criterion is the one exception in kind: failing it is
categorical, not a threshold, and the manuscript says such a participant is
excluded automatically. Even so, the exclusion is recorded rather than enforced
— the export carries the flag and the analysis drops the row, which keeps the
decision visible in the data instead of hidden in whichever code path skipped
them.

A note on the passive arm. Its criterion only became capable of firing once
participants were allowed to leave the intervention early. While everyone was
held for the full period, nobody could advance before a minimum reading time by
construction. Now they can, so the measure is live and worth watching.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .arms import Arm
from .phases import Phase, ran_out_of_time, time_in_phase


@dataclass(frozen=True)
class Measure:
    """One quantity a criterion is judged on. Reported, never thresholded."""

    #: Short name, as it appears on the console and in the export header.
    key: str
    label: str
    #: The raw number, in the unit named by :attr:`unit`. None when not yet known.
    value: float | None
    unit: str = ""

    @property
    def display(self) -> str:
        if self.value is None:
            return "—"
        if self.unit == "min":
            total = int(self.value)
            return f"{total // 60}:{total % 60:02d}"
        if self.unit == "%":
            return f"{self.value * 100:.0f}%"
        return f"{self.value:g}"

    @property
    def is_zero(self) -> bool:
        """Zero is worth surfacing on its own.

        Not because zero is an exclusion — that is the threshold's job — but
        because it usually is not a disengaged participant at all. An unguided
        participant with zero turns twenty minutes in is far more likely to be
        looking at a broken model connection, and that is fixable while the
        session is still running.
        """
        return self.value == 0


@dataclass(frozen=True)
class EngagementRecord:
    """Everything Section 4.6.3 needs about one participant, as raw numbers."""

    participant_id: str
    arm: Arm

    #: The two (or one) quantities this arm's criterion is judged on.
    measures: tuple[Measure, ...]

    #: Attention checks embedded in the surveys. Both zero until the instruments
    #: land, which is when the checks come into existence.
    attention_failed: int = 0
    attention_answered: int = 0

    #: Their intervention was ended by the clock, not by them. Descriptive.
    ran_out_of_time: bool = False

    #: Anything the proctor logged against them.
    incidents: int = 0

    #: Their arm's tool could not be started. A technical failure, and kept
    #: apart from the measures so it is never read as low engagement.
    unavailable: str = ""

    @property
    def failed_attention_check(self) -> bool:
        """The one categorical exclusion in §4.6.3."""
        return self.attention_failed > 0

    @property
    def attention_display(self) -> str:
        if self.attention_answered == 0:
            return "—"
        passed = self.attention_answered - self.attention_failed
        return f"{passed}/{self.attention_answered}"

    @property
    def needs_a_look(self) -> bool:
        """Something a proctor should check *now*, while it can still be fixed.

        Deliberately not "is likely to be excluded". Judging engagement mid-run
        and acting on it would be an intervention, and an unblinded one. This
        flags the case where a measure sitting at zero more plausibly means the
        tool is broken than that the participant is idle.
        """
        return (
            bool(self.unavailable)
            or self.incidents > 0
            or any(m.is_zero for m in self.measures)
        )

    def as_row(self) -> dict:
        """Flat form, for the export."""
        row = {
            "participant_id": self.participant_id,
            "arm": self.arm.value,
            "attention_failed": self.attention_failed,
            "attention_answered": self.attention_answered,
            "ran_out_of_time": self.ran_out_of_time,
            "incidents": self.incidents,
        }
        row.update({m.key: m.value for m in self.measures})
        return row


def build_engagement_record(participant, now: datetime, link=None) -> EngagementRecord:
    """Gather one participant's exclusion measures, whatever arm they are in.

    ``link`` is a :class:`study.senseei_link.SenseeiLink`, needed only for the
    SENSEE-I arm, whose session lives in the application rather than here.
    """
    state = participant.state
    arm = participant.arm

    if arm is Arm.SENSEEI:
        measures = _senseei_measures(participant, link)
    elif arm is Arm.UNGUIDED_LLM:
        measures = _unguided_measures(participant, now)
    else:
        measures = _passive_measures(participant, state, now)

    responses = getattr(participant, "responses", {}) or {}
    answered = sum(r.get("attention_answered", 0) for r in responses.values())
    failed = sum(r.get("attention_failed", 0) for r in responses.values())

    return EngagementRecord(
        participant_id=participant.participant_id,
        arm=arm,
        measures=measures,
        attention_failed=failed,
        attention_answered=answered,
        ran_out_of_time=ran_out_of_time(state),
        incidents=len(getattr(participant, "incidents", []) or []),
        unavailable=getattr(participant, "unavailable", "") or "",
    )


def _senseei_measures(participant, link) -> tuple[Measure, ...]:
    """§4.6.3: total session time, or number of conversational turns.

    Both come from the application through the link, because the session they
    describe happened there. A participant who never opened SENSEE-I has no
    telemetry at all, which reads as None rather than as zero — not starting and
    starting-then-stopping are different facts.
    """
    telemetry = link.fetch_telemetry(participant.participant_id) if link else None

    seconds = None
    turns = None
    if telemetry is not None:
        turns = telemetry.turn_count
        if telemetry.duration is not None:
            seconds = telemetry.duration.total_seconds()

    return (
        Measure("session_seconds", "Session time", seconds, "min"),
        Measure("turn_count", "Turns", turns),
    )


def _unguided_measures(participant, now: datetime) -> tuple[Measure, ...]:
    """§4.6.3: session length, or total word input.

    Word input counts only what the participant typed. A session of one lazy
    question answered at length is exactly the pattern this arm exists to be able
    to show, and counting the model's output would hide it.

    Session length is reported while the session is still running, measured to
    now rather than waiting for it to close. A proctor needs the number during
    the run, not only afterwards.
    """
    session = participant.unguided
    if session is None:
        return (
            Measure("session_seconds", "Session time", None, "min"),
            Measure("word_count", "Words typed", None),
        )

    conversation = session.conversation
    ended = conversation.ended_at or now
    seconds = max(0.0, (ended - conversation.started_at).total_seconds())

    return (
        Measure("session_seconds", "Session time", seconds, "min"),
        Measure("word_count", "Words typed", conversation.word_count),
    )


def _passive_measures(participant, state, now: datetime) -> tuple[Measure, ...]:
    """§4.6.3: advancing to the post-test before a realistic minimum reading time.

    Two numbers rather than one. The criterion as written is about how long they
    stayed, which is the phase duration. But phase duration cannot distinguish a
    participant who read throughout from one who closed the reading at minute six
    and sat there, so time with the text actually open is reported alongside it.
    Scroll depth is a third, weaker signal: someone who never scrolled past the
    first screen did not read a text that runs to several.
    """
    in_phase = time_in_phase(state, Phase.INTERVENTION, now)

    session = participant.passive
    on_text = None
    depth = None
    if session is not None:
        telemetry = session.telemetry()
        on_text = (
            telemetry.time_on_text.total_seconds()
            if telemetry.ended_at
            else session.time_on_text(now).total_seconds()
        )
        depth = telemetry.max_scroll_depth

    return (
        Measure("intervention_seconds", "Time before post-test",
                in_phase.total_seconds(), "min"),
        Measure("time_on_text_seconds", "Text open", on_text, "min"),
        Measure("max_scroll_depth", "Scrolled to", depth, "%"),
    )


def summarise(records: list[EngagementRecord]) -> dict:
    """Run-level counts, for the console header.

    Not an exclusion tally: nothing has been excluded, because no threshold
    exists yet. It answers "is anything obviously wrong right now".
    """
    return {
        "participants": len(records),
        "needing_a_look": sum(1 for r in records if r.needs_a_look),
        "failed_attention": sum(1 for r in records if r.failed_attention_check),
        "ran_out_of_time": sum(1 for r in records if r.ran_out_of_time),
    }


def median_of(records: list[EngagementRecord], key: str) -> float | None:
    """Median of one measure across records that have it.

    The pilot's job is to turn these distributions into the thresholds §4.6.3
    calls for, so the medians are the first thing anyone will want to see. Not a
    cutoff, and not to be used as one.
    """
    values = sorted(
        m.value
        for r in records
        for m in r.measures
        if m.key == key and m.value is not None
    )
    if not values:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2


def as_timedelta(seconds: float | None) -> timedelta | None:
    return None if seconds is None else timedelta(seconds=seconds)
