"""The session API, driven end to end.

A whole tutoring session is played through the HTTP endpoints against the test
database: start, submit responses, watch the streamed events, and check the rows
that land. The agents are replaced with a controllable stub, so a test can force
a pass, a retry, or a run of failures without calling a model.

The stub also proves the streaming path: its prose is streamed through the same
`speak_stream` -> SSE machinery the real Tutor uses.
"""

from __future__ import annotations

import json
import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agents.providers.base import LLMProvider
from agents.rubric import criteria_for, load_rubric
from backend.agent_runtime import Agents
from backend.models import Attempt, CoreComponent, Reading, Role, User

pytestmark = pytest.mark.usefixtures("fresh_engine")


# --------------------------------------------------------------------------- #
# a controllable stub standing in for both agents


def _between(text: str, header: str) -> str:
    i = text.find(header)
    if i == -1:
        return ""
    rest = text[i + len(header):]
    return rest.split("\n", 1)[0].strip()


class StubProvider(LLMProvider):
    """Deterministic provider. Fails each step until `pass_on`, then passes.

    A tutor prompt (it carries a SITUATION section) gets prose; an assessment
    prompt gets the judgment JSON. `stream()` is inherited from the base and
    yields the prose once, which is enough to exercise the streaming path.
    """

    def __init__(self, pass_on: int = 1):
        self.pass_on = pass_on
        self.seen: dict[str, int] = {}
        self.last_usage = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
        self.last_finish_reason = "STOP"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        step = _between(user_prompt, "# CURRENT SEE-I STEP\n")
        if "# SITUATION" in user_prompt:
            situation = _between(user_prompt, "# SITUATION\n")
            return f"[stub] {step}: {situation[:40]}"
        n = self.seen[step] = self.seen.get(step, 0) + 1
        passing = n >= self.pass_on
        crits = criteria_for(step)
        failed = [] if passing else crits[:1]
        return json.dumps(
            {
                "verdict": "PASS" if passing else "FAIL",
                "fail_criteria": failed,
                "criteria": {
                    c: {"pass": c not in failed, "reason": "ok" if c not in failed else "no"}
                    for c in crits
                },
            }
        )


class RaisingProvider(LLMProvider):
    """Always fails the call, to prove a provider error consumes no attempt."""

    def __init__(self):
        self.last_usage = None
        self.last_finish_reason = None

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("simulated provider outage")


def _stub_agents(assess_provider, tutor_provider) -> Agents:
    from agents.assessment import AssessmentAgent as _Assess
    from agents.tutor import TutorAgent

    return Agents(
        assessor=_Assess(assess_provider, "system"),
        tutor=TutorAgent(tutor_provider, "system"),
    )


# --------------------------------------------------------------------------- #
# SSE parsing


def parse_sse(body: str) -> list[tuple[str, dict]]:
    """Turn a raw SSE body into a list of (event, data) pairs."""
    events = []
    for block in body.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = json.loads(line[len("data:"):].strip())
        if event:
            events.append((event, data))
    return events


def kinds(events) -> list[str]:
    return [e for e, _ in events]


def message_text(events) -> str:
    """The content of the last completed message in a stream."""
    ends = [d["content"] for e, d in events if e == "message_end"]
    return ends[-1] if ends else ""


# --------------------------------------------------------------------------- #
# fixtures


@pytest.fixture
def point_app_at_test_db(test_database_url):
    """Make the app's global engine and settings use the test database.

    The streaming service opens its own session through the module-global engine,
    so the app has to be pointed at `senseei_test` for the duration of the test,
    then restored so the health tests still see the dev database.
    """
    from backend import db as db_module
    from backend.settings import get_settings

    original = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_database_url
    get_settings.cache_clear()
    yield test_database_url
    if original is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = original
    get_settings.cache_clear()


@pytest.fixture
async def seeded(point_app_at_test_db):
    """A clean test database with one student and one reading. Returns their ids."""
    load_rubric("agents/rubrics/rubric_v3.yaml")
    engine = create_async_engine(point_app_at_test_db)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(delete(User))
        await s.commit()

        instructor = User(
            role=Role.INSTRUCTOR, name="I", email="i@dlsu.edu.ph",
            google_sub="seed-instructor-1",
        )
        student = User(
            role=Role.STUDENT, name="S", email="s@dlsu.edu.ph",
            google_sub="seed-student-1",
        )
        s.add_all([instructor, student])
        await s.flush()

        reading = Reading(
            uploaded_by=instructor.id, title="Strategy",
            content="A company's strategy is a coordinated set of actions.",
        )
        s.add(reading)
        await s.flush()
        s.add_all([
            CoreComponent(reading_id=reading.id, text="coordinated actions", position=0),
        ])
        await s.commit()
        ids = {"student_id": student.id, "reading_id": reading.id}
    await engine.dispose()
    return ids


def make_client(agents) -> AsyncClient:
    from backend.deps import get_agents_dep
    from backend.main import app

    app.dependency_overrides[get_agents_dep] = lambda: agents
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _count(url, model, **where):
    engine = create_async_engine(url)
    maker = async_sessionmaker(engine)
    async with maker() as s:
        q = select(func.count()).select_from(model)
        for k, v in where.items():
            q = q.where(getattr(model, k) == v)
        n = await s.scalar(q)
    await engine.dispose()
    return n


# --------------------------------------------------------------------------- #
# tests


@pytest.mark.anyio
async def test_start_streams_the_opening_prompt(seeded):
    agents = _stub_agents(StubProvider(pass_on=1), StubProvider(pass_on=1))
    client = make_client(agents)
    try:
        r = await client.post("/sessions", json={"reading_id": str(seeded["reading_id"])})
    finally:
        from backend.main import app
        app.dependency_overrides.clear()
    assert r.status_code == 200
    events = parse_sse(r.text)
    assert kinds(events) == [
        "session", "message_start", "delta", "message_end", "state",
    ]
    session_ev = dict(events)["session"]
    assert session_ev["current_step"] == "State"
    assert session_ev["status"] == "in_progress"
    start = dict((e, d) for e, d in events)["message_start"]
    assert start["kind"] == "first_attempt"
    assert start["moves"] == ["Prompt"]


@pytest.mark.anyio
async def test_a_pass_advances_and_opens_the_next_step(seeded):
    agents = _stub_agents(StubProvider(pass_on=1), StubProvider(pass_on=1))
    client = make_client(agents)
    try:
        start = await client.post(
            "/sessions", json={"reading_id": str(seeded["reading_id"])}
        )
        session_id = dict(parse_sse(start.text))["session"]["id"]

        r = await client.post(
            f"/sessions/{session_id}/responses", json={"text": "a good answer"}
        )
        events = parse_sse(r.text)
        # the grade is never streamed to the student; only the tutor is heard
        assert "assessment" not in kinds(events)
        # a passed non-final step: acknowledge, then open the next step's prompt
        starts = [d for e, d in events if e == "message_start"]
        assert [s["kind"] for s in starts] == ["passed", "first_attempt"]
        final = next(d for e, d in events if e == "state")
        assert final["current_step"] == "Elaborate"
        assert final["terminal"] is False
        # advanced to a fresh step, so no attempts used on it yet
        assert final["attempts_used"] == 0
        assert final["attempts_left"] == 3
    finally:
        from backend.main import app
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_a_full_pass_completes_the_session(seeded):
    agents = _stub_agents(StubProvider(pass_on=1), StubProvider(pass_on=1))
    client = make_client(agents)
    try:
        start = await client.post(
            "/sessions", json={"reading_id": str(seeded["reading_id"])}
        )
        session_id = dict(parse_sse(start.text))["session"]["id"]

        last = None
        for _ in range(4):  # four steps, each passes first try
            r = await client.post(
                f"/sessions/{session_id}/responses", json={"text": "good"}
            )
            last = parse_sse(r.text)

        final = next(d for e, d in last if e == "state")
        assert final["status"] == "complete"
        assert final["terminal"] is True

        state = (await client.get(f"/sessions/{session_id}")).json()
        assert state["status"] == "complete"
    finally:
        from backend.main import app
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_a_fail_with_attempts_left_re_prompts_the_same_step(seeded):
    agents = _stub_agents(StubProvider(pass_on=2), StubProvider(pass_on=2))
    client = make_client(agents)
    try:
        start = await client.post(
            "/sessions", json={"reading_id": str(seeded["reading_id"])}
        )
        session_id = dict(parse_sse(start.text))["session"]["id"]

        r = await client.post(
            f"/sessions/{session_id}/responses", json={"text": "weak answer"}
        )
        events = parse_sse(r.text)
        # the grade stays internal; the fail is observable only as a retry message
        assert "assessment" not in kinds(events)
        starts = [d for e, d in events if e == "message_start"]
        assert [s["kind"] for s in starts] == ["retry"]
        final = next(d for e, d in events if e == "state")
        assert final["current_step"] == "State"  # stayed put
        assert final["terminal"] is False
        # one attempt spent on this step, two left
        assert final["attempts_used"] == 1
        assert final["attempts_left"] == 2
    finally:
        from backend.main import app
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_three_failures_fall_back_and_end_the_session(seeded):
    agents = _stub_agents(StubProvider(pass_on=99), StubProvider(pass_on=99))
    client = make_client(agents)
    try:
        start = await client.post(
            "/sessions", json={"reading_id": str(seeded["reading_id"])}
        )
        session_id = dict(parse_sse(start.text))["session"]["id"]

        last = None
        for _ in range(3):
            r = await client.post(
                f"/sessions/{session_id}/responses", json={"text": "no"}
            )
            last = parse_sse(r.text)

        starts = [d for e, d in last if e == "message_start"]
        # final failure: feedback, then the static fallback message
        assert [s["kind"] for s in starts] == ["final_fail", "fallback"]
        final = next(d for e, d in last if e == "state")
        assert final["status"] == "fallback"
        assert final["terminal"] is True

        # exactly three attempts were recorded, all on State
        n = await _count(
            seeded_url(), Attempt, session_id=session_id
        )
        assert n == 3

        # a fourth submission is refused
        r = await client.post(
            f"/sessions/{session_id}/responses", json={"text": "again"}
        )
        assert any(e == "error" for e, _ in parse_sse(r.text))
    finally:
        from backend.main import app
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_a_provider_failure_consumes_no_attempt(seeded):
    agents = _stub_agents(RaisingProvider(), StubProvider(pass_on=1))
    client = make_client(agents)
    try:
        start_agents = _stub_agents(StubProvider(1), StubProvider(1))
        # start the session with working agents, then swap in the failing assessor
        from backend.deps import get_agents_dep
        from backend.main import app

        app.dependency_overrides[get_agents_dep] = lambda: start_agents
        start = await client.post(
            "/sessions", json={"reading_id": str(seeded["reading_id"])}
        )
        session_id = dict(parse_sse(start.text))["session"]["id"]

        app.dependency_overrides[get_agents_dep] = lambda: agents
        r = await client.post(
            f"/sessions/{session_id}/responses", json={"text": "answer"}
        )
        events = parse_sse(r.text)
        assert any(e == "error" for e, _ in events)
        # no tutor message was produced, and crucially no attempt row: a provider
        # failure must leave the session exactly where it was
        assert "message_end" not in kinds(events)
        n = await _count(seeded_url(), Attempt, session_id=session_id)
        assert n == 0
    finally:
        from backend.main import app
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_transcript_returns_what_the_student_saw(seeded):
    agents = _stub_agents(StubProvider(pass_on=1), StubProvider(pass_on=1))
    client = make_client(agents)
    try:
        start = await client.post(
            "/sessions", json={"reading_id": str(seeded["reading_id"])}
        )
        session_id = dict(parse_sse(start.text))["session"]["id"]
        await client.post(f"/sessions/{session_id}/responses", json={"text": "good"})

        msgs = (await client.get(f"/sessions/{session_id}/messages")).json()
        # opening prompt, the passed acknowledgement, the next step's prompt
        assert len(msgs) >= 3
        assert msgs[0]["moves"] == ["Prompt"]
        assert all(m["content"] for m in msgs)
    finally:
        from backend.main import app
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_unknown_session_is_a_404(seeded):
    agents = _stub_agents(StubProvider(1), StubProvider(1))
    client = make_client(agents)
    try:
        import uuid

        r = await client.get(f"/sessions/{uuid.uuid4()}")
        assert r.status_code == 404
    finally:
        from backend.main import app
        app.dependency_overrides.clear()


def seeded_url() -> str:
    """The test database url, which is where the app now points."""
    from backend.settings import get_settings

    return get_settings().database_url
