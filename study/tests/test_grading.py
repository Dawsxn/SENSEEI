"""Blind grading and Cohen's Kappa (§4.6.5)."""

from __future__ import annotations

import pytest

from study.grading import (
    DIMENSIONS,
    LEVELS,
    RUBRIC,
    GradingError,
    Score,
    agreement,
    blind_id,
    build_blind_set,
    cohens_kappa,
    consensus_scores,
    disagreements,
    order_for,
    weighted_kappa,
)

RESPONSES = {f"P-{i:03d}": f"response text number {i}" for i in range(1, 13)}
RATERS = ("faculty-one", "faculty-two")


def score(response_id, rater, a, b, c) -> Score:
    return Score(
        response_id=response_id,
        rater=rater,
        levels=dict(zip(DIMENSIONS, (a, b, c))),
    )


# --- the rubric -----------------------------------------------------------


def test_the_rubric_is_table_4_12():
    assert DIMENSIONS == (
        "concept_retrieval",
        "scenario_application",
        "analytical_justification",
    )
    assert set(LEVELS) == {1, 2, 3}
    assert all(set(RUBRIC[d]) == {1, 2, 3} for d in DIMENSIONS)


def test_a_partial_score_is_refused():
    """Three dimensions, or it cannot be compared with the other rater's."""
    with pytest.raises(GradingError, match="unscored"):
        Score("R-1", "faculty-one", {"concept_retrieval": 3})


def test_a_level_off_the_scale_is_refused():
    with pytest.raises(GradingError, match="1, 2 or 3"):
        score("R-1", "faculty-one", 3, 4, 2)


def test_an_invented_dimension_is_refused():
    with pytest.raises(GradingError, match="not a Table 4.12 dimension"):
        Score("R-1", "faculty-one", dict(zip(DIMENSIONS, (1, 2, 3))) | {"vibes": 3})


def test_a_total_can_hide_disagreement():
    """Which is why Kappa is computed per dimension, not on the total."""
    a = score("R-1", "one", 3, 1, 2)
    b = score("R-1", "two", 1, 2, 3)
    assert a.total == b.total == 6
    assert a.levels != b.levels


# --- blinding -------------------------------------------------------------


def test_a_blind_id_reveals_nothing():
    key = blind_id("P-007", salt="trial")
    assert "P-007" not in key
    assert key.startswith("R-")


def test_a_blind_id_is_stable_so_the_two_raters_can_be_paired():
    assert blind_id("P-007", "trial") == blind_id("P-007", "trial")


def test_the_salt_separates_a_pilot_from_the_real_run():
    assert blind_id("P-007", "pilot") != blind_id("P-007", "main")


def test_the_blind_set_carries_no_participant_id():
    blind, _ = build_blind_set(RESPONSES, "trial", RATERS)
    joined = " ".join(r.response_id + r.text for r in blind)
    assert not any(pid in joined for pid in RESPONSES)


def test_the_key_maps_back_but_is_kept_separate():
    blind, key = build_blind_set(RESPONSES, "trial", RATERS)
    assert set(key.values()) == set(RESPONSES)
    assert set(key) == {r.response_id for r in blind}


def test_each_rater_gets_a_different_order():
    """Shared ordering would let agreement reflect shared context."""
    blind, _ = build_blind_set(RESPONSES, "trial", RATERS)
    first = [r.response_id for r in order_for(blind, "faculty-one")]
    second = [r.response_id for r in order_for(blind, "faculty-two")]

    assert first != second
    assert sorted(first) == sorted(second)


def test_a_rater_order_is_stable_across_visits():
    """Reloading the page must not reshuffle what they were working through."""
    blind, _ = build_blind_set(RESPONSES, "trial", RATERS)
    assert order_for(blind, "faculty-one") == order_for(blind, "faculty-one")


def test_a_representative_subset_can_be_taken():
    """§4.6.5 grades a subset, and which one must be reproducible."""
    blind, _ = build_blind_set(RESPONSES, "trial", RATERS, subset=5, seed=42)
    again, _ = build_blind_set(RESPONSES, "trial", RATERS, subset=5, seed=42)

    assert len(blind) == 5
    assert [r.response_id for r in blind] == [r.response_id for r in again]


def test_a_different_seed_selects_a_different_subset():
    a, _ = build_blind_set(RESPONSES, "trial", RATERS, subset=5, seed=1)
    b, _ = build_blind_set(RESPONSES, "trial", RATERS, subset=5, seed=2)
    assert [r.response_id for r in a] != [r.response_id for r in b]


def test_grading_needs_a_rater():
    with pytest.raises(GradingError):
        build_blind_set(RESPONSES, "trial", ())


# --- Cohen's Kappa --------------------------------------------------------


def test_perfect_agreement_is_one():
    assert cohens_kappa([1, 2, 3, 1, 2], [1, 2, 3, 1, 2]) == 1.0


def test_kappa_matches_a_hand_calculation():
    """observed 0.75, expected 23/64 → (0.75 − 0.359375) / 0.640625."""
    a = [1, 2, 3, 3, 2, 1, 1, 2]
    b = [1, 2, 3, 2, 2, 1, 2, 2]
    assert cohens_kappa(a, b) == pytest.approx(0.390625 / 0.640625)


def test_agreement_no_better_than_chance_is_about_zero():
    a = [1, 1, 2, 2, 3, 3]
    b = [1, 2, 2, 3, 3, 1]
    assert cohens_kappa(a, b) < 0.35


def test_a_single_category_throughout_is_undefined_not_perfect():
    """Chance agreement is already total; there is no room above it to measure.

    Reporting this as 1.0 would claim perfect reliability from data that cannot
    demonstrate any.
    """
    assert cohens_kappa([2, 2, 2, 2], [2, 2, 2, 2]) is None


def test_mismatched_lengths_are_refused():
    with pytest.raises(GradingError, match="same responses"):
        cohens_kappa([1, 2], [1, 2, 3])


def test_no_scores_gives_no_kappa():
    assert cohens_kappa([], []) is None


def test_weighted_kappa_is_kinder_to_adjacent_disagreement():
    """On an ordered scale, Developing-vs-Proficient is a smaller error than
    Beginning-vs-Proficient, and unweighted Kappa cannot tell them apart."""
    adjacent = ([1, 2, 3, 2, 1, 3], [1, 2, 2, 2, 1, 3])
    assert weighted_kappa(*adjacent) > cohens_kappa(*adjacent)


# --- agreement across raters ---------------------------------------------


def make_scores():
    return [
        score("R-1", "one", 3, 3, 2), score("R-1", "two", 3, 3, 2),
        score("R-2", "one", 1, 1, 1), score("R-2", "two", 1, 2, 1),
        score("R-3", "one", 2, 3, 3), score("R-3", "two", 2, 3, 3),
        score("R-4", "one", 3, 1, 2), score("R-4", "two", 1, 1, 2),
    ]


def test_agreement_is_reported_per_dimension():
    results = agreement(make_scores())
    assert set(results) == set(DIMENSIONS)
    assert results["concept_retrieval"].n == 4


def test_a_dimension_they_never_differed_on_agrees_perfectly():
    assert agreement(make_scores())["analytical_justification"].observed == 1.0


def test_kappa_needs_exactly_two_raters():
    scores = make_scores() + [score("R-1", "three", 3, 3, 2)]
    with pytest.raises(GradingError, match="exactly two raters"):
        agreement(scores)


def test_only_shared_responses_count():
    """A response one rater never reached says nothing about agreement."""
    scores = make_scores() + [score("R-9", "one", 1, 1, 1)]
    assert agreement(scores)["concept_retrieval"].n == 4


def test_interpretation_bands_are_labelled():
    results = agreement(make_scores())
    assert results["analytical_justification"].interpretation in (
        "almost perfect", "substantial", "moderate", "fair", "slight",
        "poor", "undefined",
    )


# --- disagreements and consensus -----------------------------------------


def test_disagreements_are_listed_for_the_discussion():
    found = disagreements(make_scores())
    assert {(d.response_id, d.dimension) for d in found} == {
        ("R-2", "scenario_application"),
        ("R-4", "concept_retrieval"),
    }


def test_the_widest_gaps_come_first():
    """A two-level gap is a different conversation from a one-level gap."""
    found = disagreements(make_scores())
    assert found[0].distance == 2
    assert found[0].response_id == "R-4"


def test_agreed_responses_are_not_listed():
    assert all(d.response_id != "R-3" for d in disagreements(make_scores()))


def test_consensus_keeps_what_they_already_agreed_on():
    final = consensus_scores(make_scores(), {
        ("R-2", "scenario_application"): 1,
        ("R-4", "concept_retrieval"): 2,
    })
    assert final["R-1"]["concept_retrieval"] == 3
    assert final["R-3"]["analytical_justification"] == 3


def test_consensus_uses_the_resolved_value_where_they_differed():
    final = consensus_scores(make_scores(), {
        ("R-2", "scenario_application"): 1,
        ("R-4", "concept_retrieval"): 2,
    })
    assert final["R-2"]["scenario_application"] == 1
    assert final["R-4"]["concept_retrieval"] == 2


def test_an_unresolved_disagreement_is_refused():
    """Silently picking a rater would quietly make one of them authoritative."""
    with pytest.raises(GradingError, match="no consensus was recorded"):
        consensus_scores(make_scores(), {})
