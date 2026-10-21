"""A turn that breaks partway: the browser goes away, or the model fails.

Neither may leave a session somewhere it cannot continue from. A trial
participant gets one session, so a session stuck without its opening question,
or a passed step still waiting for an answer, would end their part of the study.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.models import Session
from backend.services.detach import detached
from test_session_api import (  # noqa: F401  (`seeded` is a fixture)
    RaisingProvider,
    StubProvider,
    _count,
    _stub_agents,
    make_client,
    parse_sse,
    seeded,
)

pytestmark = pytest.mark.usefixtures("fresh_engine", "auth_seed_student")


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    from backend.main import app

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_a_turn_finishes_after_its_listener_leaves():
    done: list[str] = []

    async def turn():
        yield "first"
        await asyncio.sleep(0.05)
        done.append("saved the reply")
        yield "second"

    stream = detached(turn())
    assert await stream.__anext__() == "first"
    await stream.aclose()  # the browser went away mid-reply
    await asyncio.sleep(0.2)
    assert done == ["saved the reply"]


@pytest.mark.anyio
async def test_a_failed_opening_question_leaves_no_session_behind(seeded, point_app_at_test_db):
    client = make_client(_stub_agents(StubProvider(pass_on=1), RaisingProvider()))
    async with client:
        r = await client.post("/sessions", json={"reading_id": str(seeded["reading_id"])})
    assert parse_sse(r.text)[-1][0] == "error"
    assert await _count(point_app_at_test_db, Session) == 0


@pytest.mark.anyio
async def test_a_pass_whose_reply_fails_still_moves_the_session_on(seeded, point_app_at_test_db):
    from backend.deps import get_agents_dep
    from backend.main import app

    working = _stub_agents(StubProvider(pass_on=1), StubProvider(pass_on=1))
    no_tutor = _stub_agents(StubProvider(pass_on=1), RaisingProvider())
    client = make_client(working)
    async with client:
        start = await client.post("/sessions", json={"reading_id": str(seeded["reading_id"])})
        session_id = dict(parse_sse(start.text))["session"]["id"]
        app.dependency_overrides[get_agents_dep] = lambda: no_tutor
        r = await client.post(f"/sessions/{session_id}/responses", json={"text": "a pass"})
    assert "error" in [k for k, _ in parse_sse(r.text)]

    engine = create_async_engine(point_app_at_test_db)
    async with async_sessionmaker(engine)() as s:
        sess = await s.scalar(select(Session).where(Session.id == session_id))
    await engine.dispose()
    # The pass counted: the session is on Elaborate, not waiting on State again.
    assert sess.current_step == "Elaborate"
