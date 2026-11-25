"""The trial's Analysis tab (backend/services/analysis_service.py).

The figures are built from the export's own tables, so most of this tests
`summarize` on small hand-made tables, without a database. The API tests at
the end play a sitting through and check who may see the figures.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.services.analysis_service import summarize

P_HEADER = [
    "participant_id", "batch", "class", "group", "signed_in_at", "reading_opened_at",
    "done_at", "time_ran_out_at", "voided_at", "test",
    "pretest_started_at", "pretest_ended_at", "pretest_ended_by",
    "posttest_started_at", "posttest_ended_at", "posttest_ended_by",
    "pretest_score", "posttest_total", "calibration", "sure_but_wrong",
]
T_HEADER = [
    "participant_id", "test", "question", "part", "dimension", "kind", "answer", "sure",
    "score", "max_score", "first_answered_at", "last_changed_at", "edits", "scored_at",
]


def at(minute: int) -> str:
    return f"2026-11-23T10:{minute:02d}:00+00:00"


def person(code, group, pre, post, cal, sbw, done=None, signed=True, post_ended=True, test="t"):
    return [
        code, "Sitting 1", "C", group, at(0) if signed else "", at(5) if signed else "",
        at(done) if done else "", at(40) if signed else "", "", test,
        at(1), at(4), "submitted", at(41), at(51) if post_ended else "",
        "submitted" if post_ended else "",
        pre, post, cal, sbw,
    ]


def answers(code, facts, transfer):
    return [
        [code, "pre", "pre", "", "", "text", "x", "", 1, 3, "", "", 1, ""],
        [code, "post", "q1", "A", "facts", "truefalse", "{}", True, facts, 5, "", "", 1, ""],
        [code, "post", "q6", "C", "transfer", "text", "x", False, transfer, 3, "", "", 1, ""],
    ]


def tables(extra_events=()):
    people = [
        person("P-SEEI-DONE", "seei", 2, 8, 0.5, 1),
        person("P-SEEI-OUT1", "seei", 1, 6, 1.0, 0),
        person("P-CHAT-0001", "chatbot", 0, 4, 0.5, 1, done=20),
        person("P-READ-0001", "reading_only", 1, 7, 0.0, 2),  # never pressed Done
        # Signed in, still on the post-test: not Finished, so never counted.
        person("P-READ-LATE", "reading_only", 3, "", "", "", post_ended=False),
        person("P-NEVER-USED", "seei", "", "", "", "", signed=False),
    ]
    tests = (answers("P-SEEI-DONE", 5, 3) + answers("P-SEEI-OUT1", 3, 3)
             + answers("P-CHAT-0001", 2, 2) + answers("P-READ-0001", 4, 3))
    sessions = [
        ["P-SEEI-DONE", "s1", "R", "complete", "Illustrate", at(10), at(30), "v3", "v2", "v7", "m"],
        ["P-SEEI-OUT1", "s2", "R", "timed_out", "State", at(15), at(40), "v3", "v2", "v7", "m"],
    ]
    attempts = [
        ["P-SEEI-DONE", "s1", "State", 1, at(11), "FAIL", "FAIL", "a"],
        ["P-SEEI-DONE", "s1", "State", 2, at(12), "PASS", "PASS", "b"],
        ["P-SEEI-OUT1", "s2", "State", 1, at(16), "FAIL", "PASS", "c"],
    ]
    criteria = [
        ["P-SEEI-DONE", "s1", "State", 1, "Completeness", False, "r"],
        ["P-SEEI-DONE", "s1", "State", 1, "Brevity", True, "r"],
        ["P-SEEI-DONE", "s1", "State", 2, "Completeness", True, "r"],
        ["P-SEEI-DONE", "s1", "State", 2, "Brevity", True, "r"],
        ["P-SEEI-OUT1", "s2", "State", 1, "Completeness", False, "r"],
        ["P-SEEI-OUT1", "s2", "State", 1, "Brevity", True, "r"],
    ]
    chat = [
        ["P-CHAT-0001", "user", at(8), "what is it", "", "", ""],
        ["P-CHAT-0001", "assistant", at(9), "it is", False, "", ""],
    ]
    events = [
        ["P-SEEI-DONE", "reply_shown", "", at(11), at(11)],
        ["P-SEEI-DONE", "first_keystroke", "", "2026-11-23T10:11:30+00:00", at(11)],
        ["P-SEEI-DONE", "paste", '{"length": 120, "step": "State"}', at(12), at(12)],
        ["P-SEEI-OUT1", "tab_left", '{"stage": "posttest"}', at(45), at(45)],
        ["P-CHAT-0001", "paste", '{"length": 30, "stage": "posttest"}', at(46), at(46)],
        *extra_events,
    ]
    return {
        "participants.csv": (P_HEADER, people),
        "tests.csv": (T_HEADER, tests),
        "sessions.csv": (["participant_id", "session_id", "reading", "status", "last_step",
                          "started_at", "ended_at", "rubric_version", "tutor_prompt_version",
                          "assessment_prompt_version", "model"], sessions),
        "attempts.csv": (["participant_id", "session_id", "step", "attempt_number",
                          "submitted_at", "verdict", "model_verdict", "response_text"], attempts),
        "criteria.csv": (["participant_id", "session_id", "step", "attempt_number", "criterion",
                          "passed", "reason"], criteria),
        "chat_messages.csv": (["participant_id", "role", "created_at", "content", "searched",
                               "sources", "search"], chat),
        "events.csv": (["participant_id", "kind", "data", "at", "received_at"], events),
    }


def values(out, key):
    return next(r["values"] for r in out["comparison"]["rows"] if r["key"] == key)


def test_the_groups_and_the_seei_split():
    out = summarize(tables())
    assert (out["used"], out["unused"], out["finished"], out["included"]) == (5, 1, 4, 4)
    assert {c["key"]: c["n"] for c in out["comparison"]["columns"]} == {
        "chatbot": 1, "reading_only": 1, "seei": 2, "seei_completed": 1, "seei_not_completed": 1,
    }
    post = values(out, "posttest_total_mean")
    assert (post["seei_completed"], post["seei_not_completed"], post["seei"]) == (8, 6, 7)
    assert values(out, "posttest_total_range")["seei"] == [6, 8]
    # Shares are summed over answers, not averaged over people: (5 + 3) / 10.
    assert values(out, "dim_facts")["seei"] == 0.8
    assert out["comparison"]["posttest_max"] == 8


def test_every_measure_is_described_in_full():
    out = summarize(tables())
    rows = [r for r in out["comparison"]["rows"] if r["measure"] == "Pre-test score (out of 3)"]
    assert [r["label"] for r in rows] == ["n", "Mean", "SD", "Median", "Quartiles (Q1–Q3)", "Range"]
    seei = {r["label"]: r["values"]["seei"] for r in rows}
    # SEE-I pre-test scores 2 and 1: sample SD of two values is |a - b| / sqrt(2).
    assert seei == {"n": 2, "Mean": 1.5, "SD": 0.707, "Median": 1.5,
                    "Quartiles (Q1–Q3)": [1.25, 1.75], "Range": [1, 2]}
    # One value: no SD to give, and it is its own quartiles.
    chat = {r["label"]: r["values"]["chatbot"] for r in rows}
    assert (chat["n"], chat["SD"], chat["Quartiles (Q1–Q3)"]) == (1, None, [0, 0])
    measures = {r["measure"] for r in out["comparison"]["rows"] if r["section"] == "scores"}
    assert "Post-test score (out of 8)" in measures and "Calibration" in measures


def test_distributions_hold_each_groups_values_mean_and_sd():
    out = summarize(tables())
    post = next(d for d in out["comparison"]["distributions"] if d["key"] == "posttest_total")
    assert (post["low"], post["high"]) == (0, 8)
    assert set(post["series"]) == {"chatbot", "reading_only", "seei"}
    assert post["series"]["seei"] == {"values": [6, 8], "mean": 7, "sd": 1.414}
    assert post["series"]["chatbot"] == {"values": [4], "mean": 4, "sd": None}


def test_only_finished_ids_are_counted():
    out = summarize(tables())
    people = {p["code"]: p for p in out["participants"]}
    late = people["P-READ-LATE"]
    assert (late["finished"], late["excluded"]) == (False, False)
    assert "Not finished" in late["flags"]
    # Listed, but in no figure: the reading-only group is P-READ-0001 alone.
    assert values(out, "pretest_score_n")["reading_only"] == 1
    assert values(out, "pretest_score_mean")["reading_only"] == 1


def test_without_tests_finished_follows_the_session_done_or_the_clock():
    rows = [
        person("P-SEEI-DONE", "seei", "", "", "", "", test=""),           # session ended
        person("P-CHAT-0001", "chatbot", "", "", "", "", done=20, test=""),  # pressed Done
        person("P-READ-0001", "reading_only", "", "", "", "", test=""),     # clock runs to 10:40
    ]
    t = {**tables(), "participants.csv": (P_HEADER, rows)}
    before = summarize(t, now=datetime(2026, 11, 23, 10, 30, tzinfo=timezone.utc))
    after = summarize(t, now=datetime(2026, 11, 23, 10, 41, tzinfo=timezone.utc))
    assert {p["code"]: p["finished"] for p in before["participants"]} == {
        "P-SEEI-DONE": True, "P-CHAT-0001": True, "P-READ-0001": False,
    }
    assert all(p["finished"] for p in after["participants"])


def test_excluding_an_id_takes_it_out_of_every_figure_but_not_the_list():
    out = summarize(tables(), {"p-seei-out1"})
    assert out["included"] == 3
    assert values(out, "posttest_total_mean")["seei"] == 8
    assert values(out, "test_leavers")["seei"] == 0
    assert [s["code"] for s in out["seei"]["sessions"]] == ["P-SEEI-DONE"]
    listed = {p["code"]: p["excluded"] for p in out["participants"]}
    assert listed == {"P-SEEI-DONE": False, "P-SEEI-OUT1": True,
                      "P-CHAT-0001": False, "P-READ-0001": False, "P-READ-LATE": False}


def test_seei_steps_criteria_and_fixes():
    seei = summarize(tables())["seei"]
    state = seei["steps"][0]
    assert (state["attempts"], state["passed"], state["reached"], state["attempts_to_pass"]) == (3, 1, 2, 2)
    top = seei["criteria"][0]
    assert (top["criterion"], top["judged"], top["failed"]) == ("Completeness", 3, 2)
    # Fixed on the next attempt: only failures that had a next attempt count.
    assert seei["fixes"] == [{"criterion": "Completeness", "failed": 1, "fixed": 1, "rate": 1.0}]
    done = next(s for s in seei["sessions"] if s["code"] == "P-SEEI-DONE")
    assert (done["reading_minutes"], done["session_minutes"], done["turns"]) == (5, 20, 2)


def test_behaviour_and_flags():
    out = summarize(tables())
    people = {p["code"]: p for p in out["participants"]}
    assert people["P-SEEI-DONE"]["thinking_seconds"] == 30
    assert (people["P-SEEI-DONE"]["pastes"], people["P-SEEI-DONE"]["paste_chars"]) == (1, 120)
    # A paste during a test is counted apart from the rest.
    assert (people["P-CHAT-0001"]["pastes"], people["P-CHAT-0001"]["test_pastes"]) == (0, 1)
    assert people["P-CHAT-0001"]["chat_words"] == 3
    assert people["P-CHAT-0001"]["total_minutes"] == 15
    assert "Pasted during a test" in people["P-CHAT-0001"]["flags"]
    assert "Left the tab during a test" in people["P-SEEI-OUT1"]["flags"]
    assert "Never pressed Done" in people["P-READ-0001"]["flags"]
    assert people["P-SEEI-DONE"]["flags"] == []
    assert values(out, "pasters")["seei"] == 1


def test_empty_tables_give_empty_figures():
    out = summarize({})
    assert (out["used"], out["included"]) == (0, 0)
    assert all(c["n"] == 0 for c in out["comparison"]["columns"])
    assert out["seei"]["fixed_overall"]["rate"] is None


# --------------------------------------------------------------------------- #
# the API


from test_trial_api import (  # noqa: E402, F401  (fixtures are used by name)
    _batch,
    _clear_overrides,
    _first,
    _three_groups,
    as_participant,
    as_user,
    team,
    trial_on,
)
from test_trial_export_api import _sitting  # noqa: E402
from test_trial_groups_api import chatbot  # noqa: E402, F401
from test_trial_tests_api import setup  # noqa: E402, F401


@pytest.mark.anyio
@pytest.mark.usefixtures("fresh_engine")
async def test_the_team_sees_the_figures_by_batch_with_exclusions(team, chatbot):
    ids = await _sitting(team)
    async with as_user(team["prof"]) as prof:
        r = await prof.get("/instructor/analysis")
        assert r.status_code == 200
        body = r.json()
        # Mid-sitting: the SEE-I session and the chat are still going, so only
        # the reading-only ID, which pressed Done, is Finished and counted.
        assert (body["used"], body["finished"], body["included"]) == (3, 1, 1)
        assert {p["code"] for p in body["participants"]} == set(ids.values())
        finished = {p["code"] for p in body["participants"] if p["finished"]}
        assert finished == {ids["reading_only"]}
        assert body["seei"]["sessions"] == []
        batch = body["batches"][0]["id"]

        r = await prof.get(
            "/instructor/analysis", params={"batch": batch, "exclude": [ids["reading_only"]]}
        )
        assert r.status_code == 200
        body = r.json()
        assert body["batch_id"] == batch and body["included"] == 0

        other = "00000000-0000-0000-0000-000000000000"
        assert (await prof.get("/instructor/analysis", params={"batch": other})).status_code == 404


@pytest.mark.anyio
@pytest.mark.usefixtures("fresh_engine")
async def test_only_the_team_sees_the_figures(team):
    async with as_user(team["prof"]) as prof:
        batch = await _batch(prof, await _three_groups(prof, team["reading"]), per_class=1)
    async with as_participant(_first(batch, "seei")["code"]) as me:
        assert (await me.get("/instructor/analysis")).status_code == 403


@pytest.mark.anyio
@pytest.mark.usefixtures("fresh_engine")
async def test_the_grader_never_sees_the_figures(setup):
    """They name each ID's group, and grading is blind."""
    async with as_user(setup["grader"]) as grader:
        assert (await grader.get("/instructor/analysis")).status_code == 403
