"""Turning a participant's answers into the numbers Section 4.6.5 analyses.

Three different jobs, deliberately kept apart:

**Factual scoring.** The pre-test and post-test Part A have right answers, and
their totals feed the one-way ANOVAs that establish baseline equivalence and
check factual recall. A plain count of correct items.

**Attention checks.** Section 4.6.3 embeds them in the surveys and excludes
anyone who fails one. Counted here, and reported — never enforced. The export
carries the flag and the analysis drops the row, which keeps the decision visible
in the data instead of buried in whichever code path skipped a participant.

**The SUS composite.** Standardised and not open to interpretation: positive
items score their position minus one, negative items score five minus their
position, and the sum is multiplied by 2.5 to land on 0–100. The alternating
polarity is the point of the instrument — a participant who agrees with
everything scores in the middle rather than at the top — so a composite computed
without polarity would be wrong in a way that still looks like a plausible
number. That is why ``loader`` refuses a SUS item that does not declare one.

The SBA is not scored here at all. It is graded later by two faculty on the
three-point rubric of Table 4.12, blind and independently, and that belongs in
the grading tool rather than in a survey scorer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .schema import Instrument, Item, Polarity

#: The SUS is a five-point scale, and its composite arithmetic assumes it.
SUS_POINTS = 5
#: Ten items, each contributing 0–4, scaled by this to reach 0–100.
SUS_SCALE = 2.5


@dataclass(frozen=True)
class InstrumentResult:
    """One participant's answers to one instrument, and what they come to."""

    instrument_id: str
    answers: dict[str, str] = field(default_factory=dict)

    #: Factual items answered correctly, and how many there were.
    correct: int = 0
    scored: int = 0

    #: Attention checks failed, and how many were answered (§4.6.3).
    attention_failed: int = 0
    attention_answered: int = 0

    #: Items left blank that were required.
    missing: tuple[str, ...] = ()

    #: The SUS composite, 0–100. None for every other instrument.
    sus_score: float | None = None

    #: Familiarity ratings used for eligibility screening (§4.6.3), by item id.
    screening: dict[str, str] = field(default_factory=dict)

    @property
    def failed_attention_check(self) -> bool:
        return self.attention_failed > 0

    @property
    def is_complete(self) -> bool:
        return not self.missing

    def snapshot(self) -> dict:
        """Everything needed to reconstruct this result exactly.

        Distinct from :meth:`as_row`, which flattens for analysis and drops the
        structure. This one round-trips.
        """
        return {
            "instrument_id": self.instrument_id,
            "answers": dict(self.answers),
            "correct": self.correct,
            "scored": self.scored,
            "attention_failed": self.attention_failed,
            "attention_answered": self.attention_answered,
            "missing": list(self.missing),
            "sus_score": self.sus_score,
            "screening": dict(self.screening),
        }

    @classmethod
    def restore(cls, data: dict) -> InstrumentResult:
        return cls(
            instrument_id=data["instrument_id"],
            answers=dict(data.get("answers") or {}),
            correct=int(data.get("correct", 0)),
            scored=int(data.get("scored", 0)),
            attention_failed=int(data.get("attention_failed", 0)),
            attention_answered=int(data.get("attention_answered", 0)),
            missing=tuple(data.get("missing") or ()),
            sus_score=data.get("sus_score"),
            screening=dict(data.get("screening") or {}),
        )

    def as_row(self) -> dict:
        """Flat form, for the export."""
        row = {
            "instrument": self.instrument_id,
            "correct": self.correct,
            "scored": self.scored,
            "attention_failed": self.attention_failed,
            "attention_answered": self.attention_answered,
            "complete": self.is_complete,
        }
        if self.sus_score is not None:
            row["sus_score"] = self.sus_score
        row.update({f"item_{k}": v for k, v in self.answers.items()})
        return row


def score(instrument: Instrument, answers: dict[str, str]) -> InstrumentResult:
    """Score one submission.

    Unanswered items are not counted as wrong. A blank is an absence of evidence,
    and folding it into the score would make an incomplete submission
    indistinguishable from a participant who answered and was mistaken.
    """
    given = {k: v for k, v in answers.items() if v is not None and str(v).strip()}

    correct = 0
    scored = 0
    attention_failed = 0
    attention_answered = 0
    missing: list[str] = []
    screening: dict[str, str] = {}

    for item in instrument.items:
        answer = given.get(item.id)

        if item.required and answer is None:
            missing.append(item.id)

        if item.is_attention_check:
            if answer is not None:
                attention_answered += 1
                if not item.passed_attention(answer):
                    attention_failed += 1
            # An attention check is not a factual item: it tests whether they
            # are reading, not whether they know anything, so it never
            # contributes to a score.
            continue

        if item.is_scored:
            scored += 1
            if item.is_correct(answer):
                correct += 1

        if item.screening and answer is not None:
            screening[item.id] = answer

    return InstrumentResult(
        instrument_id=instrument.id,
        answers=given,
        correct=correct,
        scored=scored,
        attention_failed=attention_failed,
        attention_answered=attention_answered,
        missing=tuple(missing),
        sus_score=sus_composite(instrument, given),
        screening=screening,
    )


def sus_composite(instrument: Instrument, answers: dict[str, str]) -> float | None:
    """The System Usability Scale composite, 0–100 (§4.6.5).

    Returns None unless this is the SUS and every item was answered. A partial
    SUS has no composite: the scale is defined over all ten items, and scaling a
    subset up to 0–100 would produce a number that is not a SUS score while
    looking exactly like one.
    """
    if instrument.scoring != "sus" or not instrument.items:
        return None

    total = 0.0
    for item in instrument.items:
        position = _likert_position(item, answers.get(item.id))
        if position is None:
            return None
        if item.polarity is Polarity.NEGATIVE:
            total += SUS_POINTS - position
        else:
            total += position - 1

    return round(total * SUS_SCALE, 1)


def _likert_position(item: Item, answer: str | None) -> int | None:
    """Where on the scale this answer sits, 1-based, or None if unanswered.

    Taken from the option's position rather than from parsing its id, so the
    content files are free to name options however reads best.
    """
    if answer is None:
        return None
    for index, option in enumerate(item.options, start=1):
        if option.id == answer:
            return index
    return None


def combine(results: list[InstrumentResult]) -> dict:
    """Roll one participant's instruments together, for the console and export."""
    return {
        "attention_failed": sum(r.attention_failed for r in results),
        "attention_answered": sum(r.attention_answered for r in results),
        "sus_score": next(
            (r.sus_score for r in results if r.sus_score is not None), None
        ),
        "incomplete": [r.instrument_id for r in results if not r.is_complete],
    }
