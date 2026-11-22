"""Changes after the user acceptance test: on the trial site a SEE-I step has no
attempt limit, and an answer left in the box when time runs out is sent, graded,
kept and replied to, without asking again."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.models import (
    Assessment,
    Attempt,
    SeeiStep,
    SessionStatus,
    TrialEvent,
    TutorMessage,
    Verdict,
)
from backend.orchestrator import MAX_ATTEMPTS, attempt_limit, resolve
from backend.settings import get_settings
from test_session_api import StubProvider, _stub_agents, parse_sse
from test_trial_api import (  # noqa: F401  (fixtures are used by name)
    _batch,
    _clear_overrides,
    _session_of,
    _set_clock,
    _start,
    _three_groups,
    as_user,
    team,
    trial_on,
)


def test_with_no_limit_a_step_never_falls_back():
    assert attempt_limit(True) is None and attempt_limit(False) == MAX_ATTEMPTS
    d = resolve(SeeiStep.STATE, 40, Verdict.FAIL, None)
    assert d.situation == "retry" and not d.terminal and not d.fallback
    assert resolve(SeeiStep.STATE, MAX_ATTEMPTS, Verdict.FAIL).fallback  # the default keeps it


@asynccontextmanager
async def _participant(code: str, pass_on: int):
    from backend.deps import get_agents_dep
    from backend.main import app

    agents = _stub_agents(StubProvider(pass_on=pass_on), StubProvider(pass_on=1))
    app.dependency_overrides[get_agents_dep] = lambda: agents
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.post("/auth/participant", json={"code": code})).status_code == 200
        yield c


async def _seei_codes(team) -> list[str]:
    from agents.rubric import load_rubric

    load_rubric("agents/rubrics/rubric_v3.yaml")  # the stub grader judges by it
    async with as_user(team["prof"]) as prof:
        batch = await _batch(prof, await _three_groups(prof, team["reading"]))
    return [p["code"] for p in batch["participants"] if p["mode"] == "seei"]


async def _rows(url: str, session_id: str):
    engine = create_async_engine(url)
    async with async_sessionmaker(engine)() as s:
        attempts = (await s.scalars(
            select(Attempt).where(Attempt.session_id == session_id).order_by(Attempt.submitted_at)
        )).all()
        judged = await s.scalar(
            select(func.count()).select_from(Assessment)
            .join(Attempt, Attempt.id == Assessment.attempt_id)
            .where(Attempt.session_id == session_id)
        )
        replies = await s.scalar(
            select(func.count()).select_from(TutorMessage).where(TutorMessage.session_id == session_id)
        )
        events = (await s.scalars(select(TrialEvent.kind))).all()
    await engine.dispose()
    return attempts, judged, replies, events


@pytest.mark.anyio
@pytest.mark.usefixtures("fresh_engine")
async def test_a_trial_step_takes_more_than_five_tries(team, trial_on):
    code = (await _seei_codes(team))[0]
    async with _participant(code, pass_on=MAX_ATTEMPTS + 2) as me:
        await me.post("/trial/clock")
        session_id = dict(await _start(me, team["reading"]))["session"]["id"]
        for _ in range(MAX_ATTEMPTS + 1):
            r = await me.post(f"/sessions/{session_id}/responses", json={"text": "not yet"})
            state = dict(parse_sse(r.text))["state"]
            assert state["terminal"] is False and state["attempts_left"] is None, state
        r = await me.post(f"/sessions/{session_id}/responses", json={"text": "got it"})
    assert dict(parse_sse(r.text))["state"]["current_step"] == "Elaborate"


@pytest.mark.anyio
@pytest.mark.usefixtures("fresh_engine")
async def test_what_was_typed_at_time_up_is_graded_and_kept_once(team, trial_on):
    code = (await _seei_codes(team))[0]
    minutes = get_settings().trial_session_minutes
    async with _participant(code, pass_on=1) as me:
        await me.post("/trial/clock")
        session_id = dict(await _start(me, team["reading"]))["session"]["id"]
        await _set_clock(trial_on, code, minutes_ago=minutes + 1)  # a minute late
        _, _, replies_before, _ = await _rows(trial_on, session_id)

        r = await me.post(
            f"/sessions/{session_id}/responses", json={"text": "half an answer", "time_up": True}
        )
        events = parse_sse(r.text)
        assert events[-1] == ("state", {
            "status": "timed_out", "current_step": "State", "terminal": True,
            "attempts_used": 1, "attempts_left": None,
        })
        # The reply says it passed, and does not open the next step.
        assert [d["kind"] for k, d in events if k == "message_start"] == ["passed"]
        again = await me.post(
            f"/sessions/{session_id}/responses", json={"text": "more", "time_up": True}
        )
        assert parse_sse(again.text) == [("error", {"detail": "session has already ended"})]

    attempts, judged, replies, events = await _rows(trial_on, session_id)
    assert [a.response_text for a in attempts] == ["half an answer"] and judged == 1
    assert replies == replies_before + 1  # one reply, and no next question
    assert events.count("time_up_submit") == 1
    assert SessionStatus((await _session_of(trial_on, code)).status) is SessionStatus.TIMED_OUT


@pytest.mark.anyio
@pytest.mark.usefixtures("fresh_engine")
async def test_a_time_up_answer_is_taken_a_moment_early_but_not_long_after(team, trial_on):
    minutes = get_settings().trial_session_minutes

    early, late = await _seei_codes(team)
    async with _participant(early, pass_on=1) as me:
        await me.post("/trial/clock")
        session_id = dict(await _start(me, team["reading"]))["session"]["id"]
        await _set_clock(trial_on, early, minutes_ago=minutes - 1)  # their clock ran fast
        r = await me.post(f"/sessions/{session_id}/responses", json={"text": "x", "time_up": True})
    assert dict(parse_sse(r.text))["state"]["status"] == "timed_out"
    sess = await _session_of(trial_on, early)
    assert SessionStatus(sess.status) is SessionStatus.TIMED_OUT and sess.ended_at is not None

    async with _participant(late, pass_on=1) as me:
        await me.post("/trial/clock")
        session_id = dict(await _start(me, team["reading"]))["session"]["id"]
        await _set_clock(trial_on, late, minutes_ago=minutes + 10)
        r = await me.post(f"/sessions/{session_id}/responses", json={"text": "x", "time_up": True})
    assert parse_sse(r.text) == [("error", {"detail": "session has already ended"})]
