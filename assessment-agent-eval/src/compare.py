"""Compare agent output against the CSV's expected verdict + criteria, and
aggregate run-level stats (overall, per-step, per-criterion).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .rubric import canonical_criterion, criteria_for, steps


def parse_expected_criteria(criterion_targeted: str, step: str) -> list[str]:
    """Split a 'Criterion A + Criterion B' cell into canonical criterion names."""
    if not criterion_targeted or not criterion_targeted.strip():
        return []
    out: list[str] = []
    for part in criterion_targeted.split("+"):
        name = part.strip()
        if not name:
            continue
        canon = canonical_criterion(step, name)
        out.append(canon if canon else name)  # keep raw if unrecognized (visible in report)
    return out


@dataclass
class Comparison:
    expected_verdict: str
    actual_verdict: str | None
    expected_criteria: list[str]
    actual_criteria: list[str]
    matched: list[str] = field(default_factory=list)   # expected AND flagged
    missed: list[str] = field(default_factory=list)     # expected, NOT flagged
    extra: list[str] = field(default_factory=list)      # flagged, NOT expected
    verdict_match: bool = False
    criteria_exact: bool = False
    status: str = "error"   # agree | criteria_diff | verdict_diff | error


def compare(expected_verdict: str, expected_criteria, result) -> Comparison:
    ev = (expected_verdict or "").strip().upper()
    av = result.verdict
    exp = list(expected_criteria)
    act = list(result.fail_criteria)
    exp_set, act_set = set(exp), set(act)

    matched = [c for c in exp if c in act_set]
    missed = [c for c in exp if c not in act_set]
    extra = [c for c in act if c not in exp_set]
    verdict_match = av is not None and av == ev
    criteria_exact = exp_set == act_set

    if not result.parse_ok or av is None:
        status = "error"
    elif not verdict_match:
        status = "verdict_diff"
    elif criteria_exact:
        status = "agree"
    else:
        status = "criteria_diff"

    return Comparison(
        expected_verdict=ev, actual_verdict=av,
        expected_criteria=exp, actual_criteria=act,
        matched=matched, missed=missed, extra=extra,
        verdict_match=verdict_match, criteria_exact=criteria_exact, status=status,
    )


def summarize(records: list[dict]) -> dict:
    """records: list of {id, step, expected_verdict, comparison: Comparison}."""
    total = len(records)
    verdict_correct = sum(1 for r in records if r["comparison"].verdict_match)

    status_counts = {"agree": 0, "criteria_diff": 0, "verdict_diff": 0, "error": 0}
    for r in records:
        status_counts[r["comparison"].status] = status_counts.get(r["comparison"].status, 0) + 1

    per_step = []
    for s in steps():
        rs = [r for r in records if r["step"] == s]
        if not rs:
            continue
        c = sum(1 for r in rs if r["comparison"].verdict_match)
        per_step.append({"step": s, "n": len(rs), "correct": c, "accuracy": c / len(rs)})

    fail_records = [r for r in records if r["expected_verdict"].strip().upper() == "FAIL"]
    exact = sum(1 for r in fail_records if r["comparison"].criteria_exact)

    stat = defaultdict(lambda: {"expected": 0, "caught": 0, "false_flag": 0})
    for r in records:
        s, comp = r["step"], r["comparison"]
        for name in comp.expected_criteria:
            stat[(s, name)]["expected"] += 1
            if name in comp.matched:
                stat[(s, name)]["caught"] += 1
        for name in comp.extra:
            stat[(s, name)]["false_flag"] += 1

    per_criterion = []
    for s in steps():
        for name in criteria_for(s):
            st = stat.get((s, name), {"expected": 0, "caught": 0, "false_flag": 0})
            recall = (st["caught"] / st["expected"]) if st["expected"] else None
            per_criterion.append({
                "step": s, "criterion": name,
                "expected": st["expected"], "caught": st["caught"],
                "false_flag": st["false_flag"], "recall": recall,
            })

    return {
        "total": total,
        "verdict_correct": verdict_correct,
        "verdict_accuracy": verdict_correct / total if total else 0.0,
        "status_counts": status_counts,
        "per_step": per_step,
        "fail_n": len(fail_records),
        "criteria_exact": exact,
        "criteria_exact_rate": exact / len(fail_records) if fail_records else 0.0,
        "per_criterion": per_criterion,
    }
