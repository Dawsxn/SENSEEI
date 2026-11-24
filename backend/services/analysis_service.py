"""The Analysis tab: the trial's descriptive figures, for the research team.

Computed from the export's own tables (`export_service.tables`), so every figure
here is one a reader of the zip could reproduce. The study's inferential
analysis happens outside the app; this is for looking at a sitting's data on
the day, and for deciding exclusions (docs/context/trial.md).

`summarize` is pure: tables in, figures out. Only participants the batch page
calls Finished are counted (`_finished`); the rest are listed, marked, and left
out of every figure. `exclude` takes Finished IDs out of every figure too but
keeps them in the participant list, so they can be put back. Nothing here
writes or recomputes a stored answer, score or verdict.
"""

from __future__ import annotations

import json
import statistics
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import FINISHED_STATUSES
from . import export_service, trial_service
from .export_service import Table

STEPS = ("State", "Elaborate", "Exemplify", "Illustrate")
TESTS = ("pretest", "posttest")

#: The comparison's columns: the three groups side by side, then the SEE-I
#: group split by whether the session completed all four steps.
COLUMNS = (
    ("chatbot", "Chatbot"),
    ("reading_only", "Reading only"),
    ("seei", "SEE-I all"),
    ("seei_completed", "SEE-I completed"),
    ("seei_not_completed", "SEE-I not completed"),
)

#: The groups the distributions overlay: three, so each curve keeps a colour
#: that stays distinguishable from the other two wherever they overlap.
GROUPS = ("chatbot", "reading_only", "seei")

#: Every measure described in full: its key on a participant, its label, how to
#: show it, and the range it can take (None where it has no fixed bound).
MEASURES = (
    ("pretest_score", "Pre-test score", "number", 0, 3),
    ("posttest_total", "Post-test score", "number", 0, None),  # the top comes from the test
    ("calibration", "Calibration", "share", 0, 1),
    ("sure_but_wrong", "Sure but wrong", "number", 0, None),
    ("pretest_minutes", "Pre-test time", "minutes", 0, None),
    ("posttest_minutes", "Post-test time", "minutes", 0, None),
    ("total_minutes", "Time from opening the reading to the end", "minutes", 0, None),
)


# --------------------------------------------------------------------------- #
# reading the tables


def _rows(tables: dict[str, Table], name: str) -> list[dict]:
    header, rows = tables.get(name, ([], []))
    return [dict(zip(header, row)) for row in rows]


def _time(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value) if value else None


def _num(value) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _bool(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return None
    return str(value) == "True"


def _minutes(end: datetime | None, start: datetime | None) -> float | None:
    if end is None or start is None:
        return None
    return round((end - start).total_seconds() / 60, 2)


def _present(values) -> list[float]:
    return [v for v in values if v is not None]


def _mean(values) -> float | None:
    got = _present(values)
    return round(statistics.fmean(got), 3) if got else None


def _median(values) -> float | None:
    got = _present(values)
    return round(statistics.median(got), 3) if got else None


def _share(scores: list[tuple[float, float]]) -> float | None:
    top = sum(m for _, m in scores)
    return round(sum(s for s, _ in scores) / top, 3) if top else None


def _describe(values) -> dict:
    """n, mean, SD, median, quartiles and range. The SD is the sample SD (n - 1),
    so it needs two values; quartiles are inclusive, so one value is its own."""
    got = sorted(_present(values))
    if not got:
        return {"n": 0, "mean": None, "sd": None, "median": None, "q1": None, "q3": None,
                "min": None, "max": None}
    q1, _, q3 = statistics.quantiles(got, n=4, method="inclusive") if len(got) > 1 else got * 3
    r = lambda v: round(v, 3)  # noqa: E731
    return {
        "n": len(got),
        "mean": r(statistics.fmean(got)),
        "sd": r(statistics.stdev(got)) if len(got) > 1 else None,
        "median": r(statistics.median(got)),
        "q1": r(q1), "q3": r(q3),
        "min": r(got[0]), "max": r(got[-1]),
    }


def _finished(p: dict, session: dict | None, now: datetime) -> bool:
    """Finished as the batch page counts it (trial_service.get_batch): never a
    voided ID; with tests, once the post-test has ended; without, once the
    SEE-I session has ended, Done was pressed, or the time ran out."""
    if p["voided_at"]:
        return False
    if p["test"]:
        return bool(p["posttest_ended_at"])
    if session is not None and session["status"] in FINISHED_STATUSES:
        return True
    end = _time(p["time_ran_out_at"])
    return bool(p["done_at"]) or (end is not None and now >= end)


# --------------------------------------------------------------------------- #
# one participant


def _people(tables: dict[str, Table], exclude: set[str], now: datetime) -> list[dict]:
    """Everyone who signed in, with the measures the figures are made of."""
    sessions = {s["participant_id"]: s for s in _rows(tables, "sessions.csv")}
    attempts: dict[str, list[dict]] = {}
    for a in _rows(tables, "attempts.csv"):
        attempts.setdefault(a["participant_id"], []).append(a)
    chat: dict[str, list[dict]] = {}
    for m in _rows(tables, "chat_messages.csv"):
        chat.setdefault(m["participant_id"], []).append(m)
    tests: dict[str, list[dict]] = {}
    for t in _rows(tables, "tests.csv"):
        tests.setdefault(t["participant_id"], []).append(t)
    events: dict[str, list[dict]] = {}
    for e in _rows(tables, "events.csv"):
        e = {**e, "at": _time(e["at"]), "data": json.loads(e["data"]) if e["data"] else {}}
        events.setdefault(e["participant_id"], []).append(e)

    people = []
    for p in _rows(tables, "participants.csv"):
        if not p["signed_in_at"]:
            continue
        code, group = p["participant_id"], p["group"]
        opened, done = _time(p["reading_opened_at"]), _time(p["done_at"])
        session = sessions.get(code)
        mine = sorted(events.get(code, []), key=lambda e: e["at"])

        status = session["status"] if session else None
        reading_minutes = session_minutes = total_minutes = None
        if group == "seei" and session:
            reading_minutes = _minutes(_time(session["started_at"]), opened)
            session_minutes = _minutes(_time(session["ended_at"]), _time(session["started_at"]))
            total_minutes = _minutes(_time(session["ended_at"]), opened)
        elif group == "chatbot":
            last = max(
                [_time(m["created_at"]) for m in chat.get(code, [])] + ([done] if done else []),
                default=None,
            )
            session_minutes = total_minutes = _minutes(last, opened)
        elif group == "reading_only":
            session_minutes = total_minutes = _minutes(done, opened)

        asked = [m for m in chat.get(code, []) if m["role"] == "user"]

        def stage(e: dict) -> str | None:
            return e["data"].get("stage")

        pastes = [e for e in mine if e["kind"] == "paste"]
        test_pastes = [e for e in pastes if stage(e) in TESTS]
        test_leaves = [e for e in mine if e["kind"] == "tab_left" and stage(e) in TESTS]

        # Thinking time: each first keystroke straight after a reply arrived.
        thinking, previous = [], None
        for e in mine:
            if e["kind"] not in ("reply_shown", "first_keystroke"):
                continue
            if e["kind"] == "first_keystroke" and previous and previous["kind"] == "reply_shown":
                thinking.append((e["at"] - previous["at"]).total_seconds())
            previous = e

        post = [t for t in tests.get(code, []) if t["test"] == "post"]
        dimensions: dict[str, list[tuple[float, float]]] = {}
        for t in post:
            score, top = _num(t["score"]), _num(t["max_score"])
            if t["dimension"] and score is not None and top:
                dimensions.setdefault(t["dimension"], []).append((score, top))

        row = {
            "code": code,
            "batch": p["batch"],
            "group": group,
            # Finished on the batch page; only these are counted.
            "finished": _finished(p, session, now),
            "excluded": code in exclude,
            "voided": bool(p["voided_at"]),
            "status": status,
            "last_step": session["last_step"] if session else None,
            # The SEE-I session completed all four steps.
            "completed": (status == "complete") if group == "seei" else None,
            "pretest_score": _num(p["pretest_score"]),
            "posttest_total": _num(p["posttest_total"]),
            "posttest_max": sum(_num(t["max_score"]) or 0 for t in post) or None,
            "calibration": _num(p["calibration"]),
            "sure_but_wrong": _num(p["sure_but_wrong"]),
            "pretest_minutes": _minutes(_time(p["pretest_ended_at"]), _time(p["pretest_started_at"])),
            "posttest_minutes": _minutes(_time(p["posttest_ended_at"]), _time(p["posttest_started_at"])),
            "pretest_ended_by": p["pretest_ended_by"] or None,
            "posttest_ended_by": p["posttest_ended_by"] or None,
            "reading_minutes": reading_minutes,
            "session_minutes": session_minutes,
            "total_minutes": total_minutes,
            "minutes_to_done": _minutes(done, opened),
            "turns": len(attempts.get(code, [])) if group == "seei" else None,
            "chat_questions": len(asked) if group == "chatbot" else None,
            "chat_words": sum(len(str(m["content"]).split()) for m in asked) if group == "chatbot" else None,
            "pastes": len(pastes) - len(test_pastes),
            "paste_chars": sum(int(e["data"].get("length") or 0) for e in pastes if e not in test_pastes),
            "test_pastes": len(test_pastes),
            "test_tab_left": len(test_leaves),
            "thinking_seconds": _median(thinking),
            "turn_failed": sum(1 for e in mine if e["kind"] == "turn_failed"),
            "_dimensions": dimensions,
            "_thinking": thinking,
        }
        row["flags"] = _flags(row, done)
        people.append(row)
    return people


def _flags(row: dict, done: datetime | None) -> list[str]:
    """What is worth a second look before deciding on exclusions."""
    flags = []
    if not row["finished"]:
        flags.append("Not finished")
    if row["voided"]:
        flags.append("Voided")
    if row["test_pastes"]:
        flags.append("Pasted during a test")
    if row["test_tab_left"]:
        flags.append("Left the tab during a test")
    if row["group"] in ("chatbot", "reading_only") and done is None:
        flags.append("Never pressed Done")
    if row["group"] == "chatbot" and not row["chat_questions"]:
        flags.append("Sent no messages")
    if row["turn_failed"]:
        flags.append("An AI reply failed")
    if row["posttest_max"] and row["posttest_total"] is None:
        flags.append("Not fully graded")
    return flags


def _in(column: str, p: dict) -> bool:
    if column == "seei_completed":
        return p["group"] == "seei" and p["completed"] is True
    if column == "seei_not_completed":
        return p["group"] == "seei" and p["completed"] is not True
    return p["group"] == column


# --------------------------------------------------------------------------- #
# the figures


def _comparison(people: list[dict]) -> dict:
    groups = {key: [p for p in people if _in(key, p)] for key, _ in COLUMNS}
    order = {"facts": 0, "procedures": 1, "connections": 2, "transfer": 3, "metacognition": 4}
    dims = sorted({d for p in people for d in p["_dimensions"]}, key=lambda d: (order.get(d, 9), d))

    def row(key, label, fmt, fn, section, measure=None):
        return {"key": key, "label": label, "format": fmt, "section": section, "measure": measure,
                "values": {c: fn(g) for c, g in groups.items()}}

    max_post = max(_present(p["posttest_max"] for p in people), default=None)

    # Every measure in full, one block of rows each: n, mean, SD, median,
    # quartiles and range. A range-like value is [low, high].
    scores = []
    described = {key: {c: _describe(p[key] for p in g) for c, g in groups.items()}
                 for key, *_ in MEASURES}
    for key, label, fmt, _, _ in MEASURES:
        if key == "posttest_total" and max_post:
            label = f"Post-test score (out of {max_post:g})"
        elif key == "pretest_score":
            label = "Pre-test score (out of 3)"
        d = described[key]
        for name, stat_label, stat_fmt in (
            ("n", "n", "count"), ("mean", "Mean", fmt), ("sd", "SD", fmt),
            ("median", "Median", fmt), ("iqr", "Quartiles (Q1–Q3)", fmt), ("range", "Range", fmt),
        ):
            values = {}
            for c in groups:
                s = d[c]
                values[c] = (
                    [s["q1"], s["q3"]] if name == "iqr" and s["n"]
                    else [s["min"], s["max"]] if name == "range" and s["n"]
                    else None if name in ("iqr", "range")
                    else s[name]
                )
            scores.append({"key": f"{key}_{name}", "label": stat_label, "format": stat_fmt,
                           "section": "scores", "measure": label, "values": values})
    dimensions = [
        row(f"dim_{d}", d.capitalize(), "share",
            lambda g, d=d: _share([s for p in g for s in p["_dimensions"].get(d, [])]), "dimensions")
        for d in dims
    ]
    behaviour = [
        row("thinking", "Thinking time after a reply (median)", "seconds",
            lambda g: _median([t for p in g for t in p["_thinking"]]), "behaviour"),
        row("pasters", "Pasted outside the tests", "people",
            lambda g: sum(1 for p in g if p["pastes"]), "behaviour"),
        row("pastes", "Pastes outside the tests", "count",
            lambda g: sum(p["pastes"] for p in g), "behaviour"),
        row("test_pasters", "Pasted during a test", "people",
            lambda g: sum(1 for p in g if p["test_pastes"]), "behaviour"),
        row("test_leavers", "Left the tab during a test", "people",
            lambda g: sum(1 for p in g if p["test_tab_left"]), "behaviour"),
        row("test_tab_left", "Tab leaves during the tests", "count",
            lambda g: sum(p["test_tab_left"] for p in g), "behaviour"),
        row("turn_failed", "AI replies that failed", "count",
            lambda g: sum(p["turn_failed"] for p in g), "behaviour"),
    ]
    # Each group's values for every measure, with the mean and SD the bell
    # curves are drawn from. Values only, never an ID.
    distributions = []
    for key, label, fmt, low, high in MEASURES:
        if key == "posttest_total":
            high = max_post
        distributions.append({
            "key": key, "label": label, "format": fmt, "low": low, "high": high,
            "series": {
                c: {"values": sorted(_present(p[key] for p in groups[c])),
                    "mean": described[key][c]["mean"], "sd": described[key][c]["sd"]}
                for c in GROUPS
            },
        })
    return {
        "columns": [{"key": k, "label": label, "n": len(groups[k])} for k, label in COLUMNS],
        "posttest_max": max_post,
        "rows": scores + dimensions + behaviour,
        "distributions": distributions,
    }


def _seei(tables: dict[str, Table], people: list[dict]) -> dict:
    """The SEE-I sessions of the participants still in the figures."""
    included = {p["code"] for p in people if p["group"] == "seei"}
    attempts = [a for a in _rows(tables, "attempts.csv") if a["participant_id"] in included]
    judged = [c for c in _rows(tables, "criteria.csv") if c["participant_id"] in included]

    steps = []
    for step in STEPS:
        mine = [a for a in attempts if a["step"] == step]
        passes = [int(a["attempt_number"]) for a in mine if a["verdict"] == "PASS"]
        steps.append({
            "step": step,
            "attempts": len(mine),
            "pass_rate": round(len(passes) / len(mine), 3) if mine else None,
            "passed": len(passes),
            "reached": len({a["participant_id"] for a in mine}),
            "attempts_to_pass": _mean(passes),
            "most_attempts": max((int(a["attempt_number"]) for a in mine), default=None),
        })

    ok = {(c["session_id"], c["step"], c["criterion"], int(c["attempt_number"])): _bool(c["passed"])
          for c in judged}
    criteria: dict[tuple[str, str], dict] = {}
    fixes: dict[str, dict] = {}
    for (session, step, criterion, n), passed in ok.items():
        c = criteria.setdefault((step, criterion), {"step": step, "criterion": criterion,
                                                    "judged": 0, "failed": 0})
        c["judged"] += 1
        if passed:
            continue
        c["failed"] += 1
        after = ok.get((session, step, criterion, n + 1))
        if after is None:
            continue  # no next attempt on that step
        f = fixes.setdefault(criterion, {"criterion": criterion, "failed": 0, "fixed": 0})
        f["failed"] += 1
        f["fixed"] += 1 if after else 0
    for c in criteria.values():
        c["fail_rate"] = round(c["failed"] / c["judged"], 3)
    for f in fixes.values():
        f["rate"] = round(f["fixed"] / f["failed"], 3)
    failed = sum(f["failed"] for f in fixes.values())

    by_code = {p["code"]: p for p in people}
    return {
        "sessions": [
            {k: by_code[code][k] for k in ("code", "status", "last_step", "completed",
                                           "reading_minutes", "session_minutes", "turns",
                                           "pretest_score", "posttest_total")}
            for code in sorted(included)
        ],
        "steps": steps,
        "criteria": sorted(criteria.values(), key=lambda c: (-c["fail_rate"], -c["judged"])),
        "fixes": sorted(fixes.values(), key=lambda f: (-f["failed"], f["criterion"])),
        "fixed_overall": {
            "failed": failed,
            "fixed": sum(f["fixed"] for f in fixes.values()),
            "rate": round(sum(f["fixed"] for f in fixes.values()) / failed, 3) if failed else None,
            "criterion": "All",
        },
    }


def summarize(
    tables: dict[str, Table], exclude: set[str] = frozenset(), now: datetime | None = None
) -> dict:
    """The figures for these tables: Finished participants only, leaving out the
    IDs in `exclude`. `now` decides whether a running clock has run out."""
    exclude = {code.strip().upper() for code in exclude}
    everyone = _people(tables, exclude, now or datetime.now(timezone.utc))
    included = [p for p in everyone if p["finished"] and not p["excluded"]]
    unused = sum(1 for p in _rows(tables, "participants.csv") if not p["signed_in_at"])
    return {
        "used": len(everyone),
        "unused": unused,
        "finished": sum(1 for p in everyone if p["finished"]),
        "included": len(included),
        "comparison": _comparison(included),
        "seei": _seei(tables, included),
        "participants": [{k: v for k, v in p.items() if not k.startswith("_")} for p in everyone],
    }


async def analysis(
    db: AsyncSession,
    instructor_id: uuid.UUID,
    batch_id: uuid.UUID | None = None,
    exclude: set[str] = frozenset(),
) -> dict:
    """The figures for one batch, or every batch, with the batches to choose from."""
    batches = await trial_service.list_batches(db, instructor_id)
    if batch_id is not None and batch_id not in {b["id"] for b in batches}:
        raise trial_service.BatchNotFound()
    tables = await export_service.tables(db, batch_id)
    return {
        "batches": [{"id": b["id"], "name": b["name"]} for b in batches],
        "batch_id": batch_id,
        **summarize(tables, exclude),
    }
