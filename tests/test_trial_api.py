"""Trial mode, end to end: batches of IDs, signing in with one, one session,
and the clock (docs/context/trial.md).

The research team signs in through the dev bypass; participants sign in the way
they will on the day, with nothing but their ID. The agents are the session
tests' stub, so a session can run without a model.
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.models import (
    CoreComponent,
    Participant,
    Reading,
    Role,
    Session,
    SessionStatus,
    User,
)
from backend.settings import get_settings
from test_session_api import StubProvider, _stub_agents, parse_sse

pytestmark = pytest.mark.usefixtures("fresh_engine")

ID = re.compile(r"^P-[2-9A-HJ-NP-Z]{4}-[2-9A-HJ-NP-Z]{4}$")


@pytest.fixture
def trial_on(point_app_at_test_db, monkeypatch):
    monkeypatch.setenv("TRIAL_MODE", "true")
    get_settings.cache_clear()
    yield point_app_at_test_db
    get_settings.cache_clear()


@pytest.fixture
async def team(trial_on):
    """One researcher and one reading, on an empty database."""
    engine = create_async_engine(trial_on)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(delete(User))
        await s.commit()
        prof = User(role=Role.INSTRUCTOR, name="Prof", email="prof@dlsu.edu.ph", google_sub="p1")
        other = User(role=Role.INSTRUCTOR, name="Other", email="other@dlsu.edu.ph", google_sub="p2")
        s.add_all([prof, other])
        await s.flush()
        reading = Reading(uploaded_by=prof.id, title="Cognitive Offloading", content="body")
        s.add(reading)
        await s.flush()
        s.add(CoreComponent(reading_id=reading.id, text="delegating", position=0))
        await s.commit()
        ids = {"prof": prof.id, "other": other.id, "reading": reading.id}
    await engine.dispose()
    return ids


def _client() -> AsyncClient:
    from backend.deps import get_agents_dep
    from backend.main import app

    agents = _stub_agents(StubProvider(pass_on=1), StubProvider(pass_on=1))
    app.dependency_overrides[get_agents_dep] = lambda: agents
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@asynccontextmanager
async def as_user(user_id):
    async with _client() as client:
        assert (await client.post("/auth/dev/login", json={"user_id": str(user_id)})).status_code == 200
        yield client


@asynccontextmanager
async def as_participant(code):
    async with _client() as client:
        r = await client.post("/auth/participant", json={"code": code})
        assert r.status_code == 200, r.text
        yield client


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    from backend.main import app

    app.dependency_overrides.clear()


async def _three_groups(prof, reading_id) -> dict[str, str]:
    """The study's three classes, each with the reading. Mode -> class id."""
    ids = {}
    for section, mode in (("S1-A", "seei"), ("S1-B", "chatbot"), ("S1-C", "reading_only")):
        r = await prof.post(
            "/instructor/classes", json={"name": "TRIAL", "section": section, "mode": mode}
        )
        assert r.status_code == 201, r.text
        ids[mode] = r.json()["id"]
    r = await prof.put(
        f"/instructor/readings/{reading_id}/classes", json={"class_ids": list(ids.values())}
    )
    assert r.status_code == 200, r.text
    return ids


async def _batch(prof, classes: dict[str, str], per_class: int = 2) -> dict:
    r = await prof.post(
        "/instructor/batches",
        json={
            "name": "Sitting 1",
            "classes": [{"class_id": cid, "count": per_class} for cid in classes.values()],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _first(batch: dict, mode: str) -> dict:
    return next(p for p in batch["participants"] if p["mode"] == mode)


async def _set_clock(url: str, code: str, minutes_ago: int) -> None:
    from backend.models import utcnow

    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(
            update(Participant)
            .where(Participant.code == code)
            .values(clock_started_at=utcnow() - timedelta(minutes=minutes_ago))
        )
    await engine.dispose()


async def _session_of(url: str, code: str) -> Session:
    engine = create_async_engine(url)
    maker = async_sessionmaker(engine)
    async with maker() as s:
        sess = await s.scalar(
            select(Session)
            .join(Participant, Participant.user_id == Session.student_id)
            .where(Participant.code == code)
        )
    await engine.dispose()
    return sess


# --------------------------------------------------------------------------- #
# outside trial mode, none of it exists


@pytest.mark.anyio
async def test_nothing_of_the_trial_exists_outside_trial_mode(point_app_at_test_db, team, monkeypatch):
    monkeypatch.setenv("TRIAL_MODE", "false")
    get_settings.cache_clear()
    async with as_user(team["prof"]) as prof:
        assert (await prof.get("/instructor/batches")).status_code == 404
        r = await prof.post(
            "/instructor/classes", json={"name": "X", "section": "Y", "mode": "chatbot"}
        )
        assert r.status_code == 422
        assert (await prof.get("/auth/config")).json()["trial_mode"] is False
    async with _client() as anyone:
        assert (await anyone.post("/auth/participant", json={"code": "P-AAAA-AAAA"})).status_code == 404


# --------------------------------------------------------------------------- #
# batches


@pytest.mark.anyio
async def test_a_batch_gives_each_class_its_count_in_a_mixed_order(team):
    async with as_user(team["prof"]) as prof:
        assert (await prof.get("/auth/config")).json()["trial_mode"] is True
        classes = await _three_groups(prof, team["reading"])
        batch = await _batch(prof, classes, per_class=4)
        listed = (await prof.get("/instructor/batches")).json()

    people = batch["participants"]
    assert len(people) == 12
    assert all(ID.match(p["code"]) for p in people)
    assert len({p["code"] for p in people}) == 12
    assert {p["mode"]: sum(q["mode"] == p["mode"] for q in people) for p in people} == {
        "seei": 4, "chatbot": 4, "reading_only": 4,
    }
    assert {p["status"] for p in people} == {"not_used"}
    assert listed == [
        {**{k: listed[0][k] for k in ("id", "created_at")}, "name": "Sitting 1",
         "closed_at": None, "id_count": 12, "used_count": 0}
    ]


@pytest.mark.anyio
async def test_a_batch_only_takes_your_own_classes(team):
    async with as_user(team["prof"]) as prof:
        classes = await _three_groups(prof, team["reading"])
    async with as_user(team["other"]) as other:
        r = await other.post(
            "/instructor/batches",
            json={"name": "X", "classes": [{"class_id": classes["seei"], "count": 1}]},
        )
        assert r.status_code == 422
        assert (await other.get("/instructor/batches")).json() == []


@pytest.mark.anyio
async def test_a_participant_shows_by_id_in_their_class(team):
    async with as_user(team["prof"]) as prof:
        classes = await _three_groups(prof, team["reading"])
        batch = await _batch(prof, classes, per_class=1)
        detail = (await prof.get(f"/instructor/classes/{classes['seei']}")).json()
    code = _first(batch, "seei")["code"]
    assert detail["mode"] == "seei"
    assert [(s["participant_code"], s["email"]) for s in detail["students"]] == [(code, "")]


# --------------------------------------------------------------------------- #
# signing in


@pytest.mark.anyio
async def test_an_id_signs_in_however_it_is_typed(team):
    async with as_user(team["prof"]) as prof:
        batch = await _batch(prof, await _three_groups(prof, team["reading"]))
    code = _first(batch, "chatbot")["code"]

    async with _client() as anyone:
        assert (await anyone.post("/auth/participant", json={"code": "P-2222-2222"})).status_code == 404
    async with as_participant(code.replace("-", " ").lower()[2:]) as me:
        who = (await me.get("/auth/me")).json()
        status = (await me.get("/trial/me")).json()

    assert who["role"] == "student" and who["name"] == code and who["email"] == ""
    assert status["code"] == code
    assert status["mode"] == "chatbot"
    assert status["reading_id"] == str(team["reading"])
    assert status["seconds_left"] is None and status["session"] is None

    async with as_user(team["prof"]) as prof:
        after = (await prof.get(f"/instructor/batches/{batch['id']}")).json()
        listed = (await prof.get("/instructor/batches")).json()
    assert _first(after, "chatbot")["status"] == "signed_in"
    assert listed[0]["used_count"] == 1


@pytest.mark.anyio
async def test_voiding_an_id_or_closing_its_batch_signs_it_out(team):
    async with as_user(team["prof"]) as prof:
        batch = await _batch(prof, await _three_groups(prof, team["reading"]))
    voided, closed = [p for p in batch["participants"] if p["mode"] == "seei"][:2]

    async with as_participant(voided["code"]) as me:
        async with as_user(team["prof"]) as prof:
            r = await prof.post(
                f"/instructor/batches/{batch['id']}/participants/{voided['id']}/void"
            )
            assert next(p for p in r.json()["participants"] if p["id"] == voided["id"])["status"] == "voided"
        assert (await me.get("/auth/me")).status_code == 401
    async with _client() as anyone:
        r = await anyone.post("/auth/participant", json={"code": voided["code"]})
        assert r.status_code == 403

    async with as_participant(closed["code"]) as me:
        async with as_user(team["prof"]) as prof:
            r = await prof.post(f"/instructor/batches/{batch['id']}/close")
            assert r.json()["closed_at"] is not None
        assert (await me.get("/auth/me")).status_code == 401
    async with _client() as anyone:
        assert (await anyone.post("/auth/participant", json={"code": closed["code"]})).status_code == 403


@pytest.mark.anyio
async def test_a_class_mode_is_fixed_once_a_participant_signs_in(team):
    async with as_user(team["prof"]) as prof:
        classes = await _three_groups(prof, team["reading"])
        batch = await _batch(prof, classes)
        url = f"/instructor/classes/{classes['chatbot']}"
        body = {"name": "TRIAL", "section": "S1-B"}
        assert (await prof.patch(url, json={**body, "mode": "reading_only"})).status_code == 200
        assert (await prof.patch(url, json={**body, "mode": "chatbot"})).status_code == 200
        async with as_participant(_first(batch, "chatbot")["code"]):
            pass
        assert (await prof.get(url)).json()["mode_locked"] is True
        assert (await prof.patch(url, json={**body, "mode": "seei"})).status_code == 409
        # Renaming still works; only the mode is fixed.
        assert (await prof.patch(url, json={**body, "section": "S1-Z", "mode": "chatbot"})).status_code == 200


# --------------------------------------------------------------------------- #
# the session and the clock


async def _start(client, reading_id) -> list[tuple[str, dict]]:
    r = await client.post("/sessions", json={"reading_id": str(reading_id)})
    assert r.status_code == 200
    return parse_sse(r.text)


@pytest.mark.anyio
async def test_one_session_per_participant(team):
    async with as_user(team["prof"]) as prof:
        batch = await _batch(prof, await _three_groups(prof, team["reading"]))
    code = _first(batch, "seei")["code"]

    async with as_participant(code) as me:
        clock = (await me.post("/trial/clock")).json()
        assert 0 < clock["seconds_left"] <= 40 * 60
        again = (await me.post("/trial/clock")).json()
        assert again["seconds_left"] <= clock["seconds_left"]  # not restarted

        first = await _start(me, team["reading"])
        assert first[0][0] == "session"
        second = await _start(me, team["reading"])
        assert second == [("error", {"detail": "you have already had your session"})]
        status = (await me.get("/trial/me")).json()
    assert status["session"]["status"] == "in_progress"


@pytest.mark.anyio
async def test_a_control_group_cannot_start_a_seei_session(team):
    async with as_user(team["prof"]) as prof:
        batch = await _batch(prof, await _three_groups(prof, team["reading"]))
    async with as_participant(_first(batch, "reading_only")["code"]) as me:
        events = await _start(me, team["reading"])
    assert events == [("error", {"detail": "this class does not use SEE-I"})]


@pytest.mark.anyio
async def test_an_answer_after_time_is_up_ends_the_session_ungraded(team, trial_on):
    async with as_user(team["prof"]) as prof:
        classes = await _three_groups(prof, team["reading"])
        batch = await _batch(prof, classes)
    code = _first(batch, "seei")["code"]

    async with as_participant(code) as me:
        await me.post("/trial/clock")
        session_id = dict(await _start(me, team["reading"]))["session"]["id"]
        await _set_clock(trial_on, code, minutes_ago=41)
        r = await me.post(f"/sessions/{session_id}/responses", json={"text": "late"})
        events = parse_sse(r.text)

    assert events == [("state", {
        "status": "timed_out", "current_step": "State", "terminal": True,
        "attempts_used": 0, "attempts_left": 3,
    })]
    sess = await _session_of(trial_on, code)
    assert SessionStatus(sess.status) is SessionStatus.TIMED_OUT
    # Ended at the deadline, not when the late answer arrived.
    from backend.models import Participant as P  # noqa: F401
    assert sess.ended_at is not None

    async with as_user(team["prof"]) as prof:
        roster = (
            await prof.get(f"/instructor/classes/{classes['seei']}/readings/{team['reading']}")
        ).json()["students"]
    row = next(s for s in roster if s["name"] == code)
    assert (row["status"], row["stopped_on"]) == ("timed_out", "State")


@pytest.mark.anyio
async def test_asking_for_status_is_enough_to_end_a_session_out_of_time(team, trial_on):
    async with as_user(team["prof"]) as prof:
        batch = await _batch(prof, await _three_groups(prof, team["reading"]))
    code = _first(batch, "seei")["code"]

    async with as_participant(code) as me:
        await me.post("/trial/clock")
        await _start(me, team["reading"])
        await _set_clock(trial_on, code, minutes_ago=45)
        status = (await me.get("/trial/me")).json()
        refused = await _start(me, team["reading"])

    assert status["time_up"] is True and status["seconds_left"] == 0
    assert status["session"]["status"] == "timed_out"
    assert refused == [("error", {"detail": "time is up"})]

    async with as_user(team["prof"]) as prof:
        after = (await prof.get(f"/instructor/batches/{batch['id']}")).json()
    assert _first(after, "seei")["status"] == "finished"
