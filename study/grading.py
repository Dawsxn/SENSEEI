"""Blind grading of the SBA, and the inter-rater reliability it has to establish.

Section 4.6.5 turns the study's primary outcome into a number this way: two
RVRCOB faculty independently and blindly grade a representative subset of the
written responses on a three-point analytical rubric, Cohen's Kappa measures how
far they agreed, and the discrepancies are settled by structured discussion.

Three properties this module exists to protect.

**Blind means blind.** A rater must not be able to tell which arm a response came
from, and must not be able to infer it from the order responses arrive in. So a
response is identified by a key that carries no arm and no participant id, and
the order is shuffled independently for each rater. Losing this loses the study's
defence against evaluator bias (§4.7.5), and no amount of care afterwards
recovers it.

**Independent means independent.** The two raters score the same responses under
the same keys — that pairing is what makes Kappa computable — but neither sees
the other's scores until both are in.

**The rubric is not free-form.** Table 4.12 fixes three dimensions and three
levels, and a rater who invents a fourth level or skips a dimension produces a
score that cannot be compared with the other rater's. The scale is enforced here
rather than trusted.

A note on the statistic. Section 4.6.5 specifies Cohen's Kappa, which is what
:func:`cohens_kappa` computes and what should be reported. It treats every
disagreement as equally bad, which for an ordered three-point scale is arguably
harsh — one rater saying Developing where the other said Proficient is a smaller
disagreement than Beginning against Proficient, and unweighted Kappa cannot tell
them apart. :func:`weighted_kappa` is provided for that reason, as something to
look at alongside rather than instead of.
"""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from dataclasses import dataclass, field

#: Table 4.12. The order is the order they are graded in, and the order they
#: appear in every export.
DIMENSIONS: tuple[str, ...] = (
    "concept_retrieval",
    "scenario_application",
    "analytical_justification",
)

DIMENSION_LABELS: dict[str, str] = {
    "concept_retrieval": "Concept Retrieval",
    "scenario_application": "Scenario Application",
    "analytical_justification": "Analytical Justification",
}

#: The three levels, scored 1–3. Descriptions are Table 4.12's, condensed to what
#: a rater needs in front of them while grading.
LEVELS: dict[int, str] = {
    1: "Beginning",
    2: "Developing",
    3: "Proficient",
}

RUBRIC: dict[str, dict[int, str]] = {
    "concept_retrieval": {
        1: "Fails to form a valid textbase; cannot retrieve relevant concepts "
           "from the reading.",
        2: "Forms a partial textbase; retrieves concepts but includes factual "
           "inaccuracies.",
        3: "Forms a clear, accurate textbase; correctly retrieves the core "
           "concepts needed for the case.",
    },
    "scenario_application": {
        1: "Fails to achieve transfer; restates facts without addressing the "
           "novel business case.",
        2: "Attempts application, but mapping is flawed, failing to achieve "
           "High Road Transfer.",
        3: "Achieves High Road Transfer; correctly applies concepts to the "
           "specific scenario variables presented in the case.",
    },
    "analytical_justification": {
        1: "Fails to construct a situation model; provides no analytical "
           "reasoning for the solution.",
        2: "Constructs a fragmented situation model; reasoning is weak or "
           "disconnected.",
        3: "Constructs a coherent situation model; analyzes the scenario using "
           "text-grounded logic.",
    },
}


class GradingError(ValueError):
    """A score that cannot be compared with another rater's."""


@dataclass(frozen=True)
class BlindResponse:
    """One SBA response as a rater sees it: text, and nothing else.

    No arm, no participant id, no position in the cohort. ``response_id`` is
    derived from the participant id through a one-way hash with the trial's own
    salt, so it is stable across raters — which is what lets their scores be
    paired for Kappa — while telling a rater nothing.
    """

    response_id: str
    text: str

    @property
    def word_count(self) -> int:
        return len(self.text.split())


@dataclass(frozen=True)
class Score:
    """One rater's judgment of one response."""

    response_id: str
    rater: str
    #: dimension name -> 1, 2 or 3
    levels: dict[str, int] = field(default_factory=dict)
    note: str = ""

    def __post_init__(self) -> None:
        missing = [d for d in DIMENSIONS if d not in self.levels]
        if missing:
            raise GradingError(
                f"{self.rater} left {', '.join(missing)} unscored on "
                f"{self.response_id}. Table 4.12 has three dimensions and a "
                "partial score cannot be compared with the other rater's."
            )
        for dimension, level in self.levels.items():
            if dimension not in DIMENSIONS:
                raise GradingError(f"{dimension!r} is not a Table 4.12 dimension.")
            if level not in LEVELS:
                raise GradingError(
                    f"{self.rater} scored {dimension} as {level!r} on "
                    f"{self.response_id}; the scale is 1, 2 or 3."
                )

    @property
    def total(self) -> int:
        """Sum across the three dimensions, 3–9.

        Reported, but the per-dimension scores are the finer instrument and the
        ones Kappa is computed on: two raters can reach the same total while
        disagreeing on every dimension.
        """
        return sum(self.levels[d] for d in DIMENSIONS)


def blind_id(participant_id: str, salt: str) -> str:
    """A stable, arm-free identifier for one response.

    One-way, so a rater who somehow obtained the list could not reverse it, and
    salted per trial so the same participant id does not produce the same key in
    a pilot and in the real run.
    """
    digest = hashlib.sha256(f"{salt}:{participant_id}".encode("utf-8")).hexdigest()
    return f"R-{digest[:10]}"


def build_blind_set(
    responses: dict[str, str],
    salt: str,
    raters: tuple[str, ...],
    subset: int | None = None,
    seed: int = 0,
) -> tuple[list[BlindResponse], dict[str, str]]:
    """Prepare the blind grading set, and the key that maps back.

    ``responses`` is participant id to SBA text. Returns the blind responses and
    a separate mapping from ``response_id`` back to participant id — separate
    because the raters receive the first and must never receive the second.

    ``subset`` selects the "representative subset" of §4.6.5 at random from a
    seeded generator, so which responses were graded is reproducible and can be
    stated in the write-up rather than being whatever someone happened to pick.
    """
    if not raters:
        raise GradingError("Blind grading needs at least one rater.")

    items = sorted(responses.items())
    rng = random.Random(seed)

    if subset is not None and subset < len(items):
        items = rng.sample(items, subset)

    blind = [
        BlindResponse(response_id=blind_id(participant_id, salt), text=text)
        for participant_id, text in items
    ]
    key = {b.response_id: participant_id for b, (participant_id, _) in zip(blind, items)}
    return blind, key


def order_for(responses: list[BlindResponse], rater: str, seed: int = 0) -> list[BlindResponse]:
    """The order one rater sees. Shuffled per rater, deterministically.

    Independent orders matter beyond tidiness: if both raters worked through the
    same sequence, a run of similar responses would land on both in the same
    place, and their agreement would partly reflect shared context rather than
    shared judgment.
    """
    shuffled = list(responses)
    random.Random(f"{seed}:{rater}").shuffle(shuffled)
    return shuffled


# --- inter-rater reliability ---------------------------------------------


@dataclass(frozen=True)
class Agreement:
    """How far two raters agreed on one dimension."""

    dimension: str
    n: int
    observed: float
    expected: float
    kappa: float | None
    weighted: float | None

    @property
    def interpretation(self) -> str:
        """Landis and Koch's conventional bands, for orientation only."""
        if self.kappa is None:
            return "undefined"
        for threshold, label in (
            (0.81, "almost perfect"),
            (0.61, "substantial"),
            (0.41, "moderate"),
            (0.21, "fair"),
            (0.01, "slight"),
        ):
            if self.kappa >= threshold:
                return label
        return "poor"


def cohens_kappa(a: list[int], b: list[int]) -> float | None:
    """Cohen's Kappa for two raters over the same items (§4.6.5).

    Returns None when Kappa is undefined — which happens when both raters used
    exactly one category throughout, so chance agreement is already 1 and there
    is no room above it to measure. That is not perfect reliability and must not
    be reported as 1.0; it means the data cannot answer the question.
    """
    if len(a) != len(b):
        raise GradingError("Both raters must have scored the same responses.")
    if not a:
        return None

    n = len(a)
    observed = sum(1 for x, y in zip(a, b) if x == y) / n

    count_a, count_b = Counter(a), Counter(b)
    expected = sum(
        (count_a.get(level, 0) / n) * (count_b.get(level, 0) / n) for level in LEVELS
    )

    if expected >= 1.0:
        return None
    return (observed - expected) / (1 - expected)


def weighted_kappa(a: list[int], b: list[int]) -> float | None:
    """Linearly weighted Kappa, for the ordinal scale.

    Supplementary to the Cohen's Kappa §4.6.5 specifies. Unweighted Kappa counts
    Developing-against-Proficient as the same failure as
    Beginning-against-Proficient; on an ordered scale that overstates the
    disagreement. Report Cohen's; look at this one too.
    """
    if len(a) != len(b):
        raise GradingError("Both raters must have scored the same responses.")
    if not a:
        return None

    n = len(a)
    span = max(LEVELS) - min(LEVELS)

    def weight(x: int, y: int) -> float:
        return 1 - abs(x - y) / span

    observed = sum(weight(x, y) for x, y in zip(a, b)) / n

    count_a, count_b = Counter(a), Counter(b)
    expected = sum(
        weight(x, y) * (count_a.get(x, 0) / n) * (count_b.get(y, 0) / n)
        for x in LEVELS
        for y in LEVELS
    )

    if expected >= 1.0:
        return None
    return (observed - expected) / (1 - expected)


def agreement(scores: list[Score]) -> dict[str, Agreement]:
    """Per-dimension agreement between exactly two raters.

    Only responses both raters scored are used. A response one rater missed
    cannot contribute to a measure of whether they agreed.
    """
    raters = sorted({s.rater for s in scores})
    if len(raters) != 2:
        raise GradingError(
            f"Cohen's Kappa compares exactly two raters; found {len(raters)}."
        )

    first, second = raters
    by_rater = {
        rater: {s.response_id: s for s in scores if s.rater == rater}
        for rater in raters
    }
    shared = sorted(set(by_rater[first]) & set(by_rater[second]))

    results: dict[str, Agreement] = {}
    for dimension in DIMENSIONS:
        a = [by_rater[first][r].levels[dimension] for r in shared]
        b = [by_rater[second][r].levels[dimension] for r in shared]
        n = len(shared)
        results[dimension] = Agreement(
            dimension=dimension,
            n=n,
            observed=(sum(1 for x, y in zip(a, b) if x == y) / n) if n else 0.0,
            expected=0.0 if not n else _expected(a, b),
            kappa=cohens_kappa(a, b),
            weighted=weighted_kappa(a, b),
        )
    return results


def _expected(a: list[int], b: list[int]) -> float:
    n = len(a)
    count_a, count_b = Counter(a), Counter(b)
    return sum(
        (count_a.get(level, 0) / n) * (count_b.get(level, 0) / n) for level in LEVELS
    )


@dataclass(frozen=True)
class Disagreement:
    """One response the raters scored differently. Input to the discussion."""

    response_id: str
    dimension: str
    levels: dict[str, int]

    @property
    def distance(self) -> int:
        values = list(self.levels.values())
        return max(values) - min(values)


def disagreements(scores: list[Score]) -> list[Disagreement]:
    """Every response and dimension the two raters scored differently.

    §4.6.5 resolves these "through a structured discussion until a consensus is
    reached", so the list is the agenda for that discussion. Sorted by distance
    first: a two-level gap is a different conversation from a one-level one.
    """
    raters = sorted({s.rater for s in scores})
    if len(raters) != 2:
        raise GradingError(
            f"Disagreement is between exactly two raters; found {len(raters)}."
        )

    first, second = raters
    by_rater = {
        rater: {s.response_id: s for s in scores if s.rater == rater}
        for rater in raters
    }

    found: list[Disagreement] = []
    for response_id in sorted(set(by_rater[first]) & set(by_rater[second])):
        for dimension in DIMENSIONS:
            levels = {
                first: by_rater[first][response_id].levels[dimension],
                second: by_rater[second][response_id].levels[dimension],
            }
            if len(set(levels.values())) > 1:
                found.append(
                    Disagreement(
                        response_id=response_id, dimension=dimension, levels=levels
                    )
                )

    return sorted(found, key=lambda d: (-d.distance, d.response_id, d.dimension))


def consensus_scores(scores: list[Score], resolved: dict[tuple[str, str], int]) -> dict[str, dict[str, int]]:
    """Final per-response scores, once the discussion has settled the differences.

    ``resolved`` maps (response_id, dimension) to the agreed level. Where the
    raters already agreed, their common score stands and no entry is needed.
    Raises if a genuine disagreement was left unresolved, rather than silently
    picking one rater — which would quietly make one of them authoritative.
    """
    raters = sorted({s.rater for s in scores})
    by_rater = {
        rater: {s.response_id: s for s in scores if s.rater == rater}
        for rater in raters
    }
    shared = sorted(set.intersection(*(set(v) for v in by_rater.values())))

    final: dict[str, dict[str, int]] = {}
    unresolved: list[str] = []

    for response_id in shared:
        final[response_id] = {}
        for dimension in DIMENSIONS:
            levels = {by_rater[r][response_id].levels[dimension] for r in raters}
            if len(levels) == 1:
                final[response_id][dimension] = levels.pop()
            elif (response_id, dimension) in resolved:
                final[response_id][dimension] = resolved[(response_id, dimension)]
            else:
                unresolved.append(f"{response_id}/{dimension}")

    if unresolved:
        raise GradingError(
            "These were scored differently and no consensus was recorded: "
            + ", ".join(unresolved)
        )
    return final
