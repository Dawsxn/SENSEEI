from types import SimpleNamespace

import pytest

from agents.rubric import criteria_for, load_rubric
from src.compare import compare, criterion_cells, summarize


@pytest.fixture(autouse=True)
def rubric_v3(restore_rubric):
    from conftest import REPO
    load_rubric(REPO / "agents/rubrics/rubric_v3.yaml")


def result(verdict, fails, ok=True):
    return SimpleNamespace(verdict=verdict, fail_criteria=list(fails), parse_ok=ok)


def record(step, expected_verdict, expected, res):
    return {"id": "x", "step": step, "expected_verdict": expected_verdict,
            "comparison": compare(expected_verdict, expected, res)}


def test_every_criterion_of_the_step_is_judged_once():
    comp = compare("FAIL", ["Brevity", "Clarity"], result("FAIL", ["Brevity", "Accuracy"]))
    cells = dict(criterion_cells("State", comp))
    assert list(cells) == list(criteria_for("State"))
    # Brevity: both fail. Clarity: missed. Accuracy: flagged but not expected. The rest: both pass.
    assert cells["Brevity"] and not cells["Clarity"] and not cells["Accuracy"]
    assert sum(cells.values()) == len(cells) - 2


def test_an_unjudged_response_matches_on_nothing():
    comp = compare("PASS", [], result(None, [], ok=False))
    assert not any(ok for _, ok in criterion_cells("State", comp))


def test_a_name_outside_the_rubric_counts_as_a_mismatch():
    comp = compare("FAIL", ["Made Up"], result("FAIL", []))
    cells = dict(criterion_cells("State", comp))
    assert cells["Made Up"] is False and len(cells) == len(criteria_for("State")) + 1


def test_summary_totals_criteria_overall_per_step_and_per_criterion():
    n_state, n_ill = len(criteria_for("State")), len(criteria_for("Illustrate"))
    records = [
        record("State", "PASS", [], result("PASS", [])),                      # all match
        record("State", "FAIL", ["Clarity"], result("FAIL", ["Brevity"])),    # 2 wrong
        record("Illustrate", "FAIL", ["Match"], result("FAIL", ["Match"])),   # all match
    ]
    s = summarize(records)
    assert s["criteria_cells"] == 2 * n_state + n_ill
    assert s["criteria_cells_correct"] == 2 * n_state + n_ill - 2
    assert s["criteria_cell_accuracy"] == pytest.approx(s["criteria_cells_correct"] / s["criteria_cells"])
    state = next(p for p in s["per_step"] if p["step"] == "State")
    assert (state["cells_correct"], state["cells"]) == (2 * n_state - 2, 2 * n_state)
    clarity = next(c for c in s["per_criterion"] if (c["step"], c["criterion"]) == ("State", "Clarity"))
    assert (clarity["cells_correct"], clarity["cells"]) == (1, 2)
    unused = next(c for c in s["per_criterion"] if c["step"] == "Elaborate")
    assert unused["cells"] == 0 and unused["cell_accuracy"] is None
