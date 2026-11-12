"""Classes and enrolment, through the real sign-in.

These tests sign in through the dev bypass rather than overriding the current
user, because the role checks are part of what is under test: an instructor
must not join classes, a student must not manage them, and one instructor must
not see another's.
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.models import (
    Class,
    Enrolment,
    Reading,
    ReadingAssignment,
    Role,
    SeeiStep,
    Session,
    SessionStatus,
    User,
    utcnow,
)

pytestmark = pytest.mark.usefixtures("fresh_engine")

CODE = re.compile(r"^[2-9A-HJ-NP-Z]{4}-[2-9A-HJ-NP-Z]{4}$")


@pytest.fixture
async def people(point_app_at_test_db):
    """Two instructors, two students, and one existing class with a reading and a
    finished session in it, so removal and deletion have something to take away."""
    engine = create_async_engine(point_app_at_test_db)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(delete(User))
        await s.commit()

        prof = User(role=Role.INSTRUCTOR, name="Prof", email="prof@dlsu.edu.ph", google_sub="p1")
        other_prof = User(role=Role.INSTRUCTOR, name="Other", email="other@dlsu.edu.ph", google_sub="p2")
        stu = User(role=Role.STUDENT, name="Stu", email="stu@dlsu.edu.ph", google_sub="s1")
        new_stu = User(role=Role.STUDENT, name="New", email="new@dlsu.edu.ph", google_sub="s2")
        s.add_all([prof, other_prof, stu, new_stu])
        await s.flush()

        klass = Class(instructor_id=prof.id, name="STRAMA", section="K31", join_code="4KQ2-9TXM")
        reading = Reading(uploaded_by=prof.id, title="Strategy", content="body")
        s.add_all([klass, reading])
        await s.flush()
        s.add_all([
            Enrolment(student_id=stu.id, class_id=klass.id),
            ReadingAssignment(reading_id=reading.id, class_id=klass.id),
        ])
        started = utcnow() - timedelta(days=1)
        done = Session(
            student_id=stu.id, reading_id=reading.id, status=SessionStatus.COMPLETE,
            current_step=SeeiStep.ILLUSTRATE, started_at=started,
            ended_at=started + timedelta(minutes=10), rubric_version="v3",
            tutor_prompt_version="v2", assessment_prompt_version="v3", llm_model="test",
        )
        s.add(done)
        await s.commit()
        ids = {
            "prof": prof.id, "other_prof": other_prof.id, "stu": stu.id,
            "new_stu": new_stu.id, "class": klass.id, "reading": reading.id,
            "session": done.id,
        }
    await engine.dispose()
    return ids


@asynccontextmanager
async def signed_in(user_id):
    """A client carrying that user's session cookie."""
    from backend.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/auth/dev/login", json={"user_id": str(user_id)})
        assert r.status_code == 200
        yield client


# --------------------------------------------------------------------------- #
# an instructor's classes


@pytest.mark.anyio
async def test_creating_a_class_issues_a_readable_code(people):
    async with signed_in(people["prof"]) as prof:
        r = await prof.post("/instructor/classes", json={"name": " STSWENG ", "section": "S11"})
        listed = (await prof.get("/instructor/classes")).json()

    assert r.status_code == 201
    body = r.json()
    # trimmed, and no 0/O or 1/I anywhere in the code
    assert (body["name"], body["section"], body["label"]) == ("STSWENG", "S11", "STSWENG S11")
    assert CODE.match(body["join_code"])
    assert {c["label"] for c in listed} == {"STRAMA K31", "STSWENG S11"}


@pytest.mark.anyio
async def test_the_same_class_twice_is_refused_ignoring_case(people):
    async with signed_in(people["prof"]) as prof:
        r = await prof.post("/instructor/classes", json={"name": "strama", "section": "k31"})
    assert r.status_code == 409


@pytest.mark.anyio
async def test_a_blank_section_is_refused(people):
    async with signed_in(people["prof"]) as prof:
        r = await prof.post("/instructor/classes", json={"name": "STRAMA", "section": "   "})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_another_instructors_class_does_not_exist_for_you(people):
    cid = people["class"]
    async with signed_in(people["other_prof"]) as other:
        assert (await other.get("/instructor/classes")).json() == []
        assert (await other.get(f"/instructor/classes/{cid}")).status_code == 404
        assert (await other.patch(f"/instructor/classes/{cid}", json={"name": "X", "section": "Y"})).status_code == 404
        assert (await other.delete(f"/instructor/classes/{cid}")).status_code == 404


@pytest.mark.anyio
async def test_students_cannot_manage_classes_and_instructors_cannot_join(people):
    async with signed_in(people["stu"]) as stu:
        assert (await stu.get("/instructor/classes")).status_code == 403
    async with signed_in(people["prof"]) as prof:
        assert (await prof.post("/enrolments", json={"join_code": "4KQ2-9TXM"})).status_code == 403


@pytest.mark.anyio
async def test_the_class_page_lists_roster_and_readings(people):
    async with signed_in(people["prof"]) as prof:
        body = (await prof.get(f"/instructor/classes/{people['class']}")).json()
    assert [s["email"] for s in body["students"]] == ["stu@dlsu.edu.ph"]
    assert [r["title"] for r in body["readings"]] == ["Strategy"]


@pytest.mark.anyio
async def test_editing_changes_what_students_see(people):
    async with signed_in(people["prof"]) as prof:
        r = await prof.patch(f"/instructor/classes/{people['class']}", json={"name": "STRAMA", "section": "K32"})
    assert r.json()["label"] == "STRAMA K32"
    async with signed_in(people["stu"]) as stu:
        rows = (await stu.get("/readings")).json()
    assert [row["class_name"] for row in rows] == ["STRAMA K32"]


# --------------------------------------------------------------------------- #
# joining


@pytest.mark.anyio
async def test_joining_accepts_the_code_however_it_is_typed(people):
    async with signed_in(people["new_stu"]) as new:
        assert (await new.get("/readings")).json() == []
        r = await new.post("/enrolments", json={"join_code": " 4kq2 9txm "})
        assert r.status_code == 200
        assert r.json()["label"] == "STRAMA K31"
        assert r.json()["reading_count"] == 1
        assert [row["title"] for row in (await new.get("/readings")).json()] == ["Strategy"]

        # a second join is quiet, not an error, and not a second enrolment
        assert (await new.post("/enrolments", json={"join_code": "4KQ2-9TXM"})).status_code == 200
    async with signed_in(people["prof"]) as prof:
        roster = (await prof.get(f"/instructor/classes/{people['class']}")).json()["students"]
    assert sorted(s["email"] for s in roster) == ["new@dlsu.edu.ph", "stu@dlsu.edu.ph"]


@pytest.mark.anyio
async def test_a_wrong_code_is_a_404(people):
    async with signed_in(people["new_stu"]) as new:
        r = await new.post("/enrolments", json={"join_code": "4KQ2-9TXN"})
    assert r.status_code == 404


@pytest.mark.anyio
async def test_a_new_code_retires_the_old_one_but_keeps_everyone_in(people):
    async with signed_in(people["prof"]) as prof:
        fresh = (await prof.post(f"/instructor/classes/{people['class']}/join-code")).json()["join_code"]
    assert CODE.match(fresh) and fresh != "4KQ2-9TXM"

    async with signed_in(people["new_stu"]) as new:
        assert (await new.post("/enrolments", json={"join_code": "4KQ2-9TXM"})).status_code == 404
        assert (await new.post("/enrolments", json={"join_code": fresh})).status_code == 200
    async with signed_in(people["stu"]) as stu:
        # already in before the change, still in after it
        assert len((await stu.get("/readings")).json()) == 1


# --------------------------------------------------------------------------- #
# removing and deleting take access away, not data


@pytest.mark.anyio
async def test_removing_a_student_takes_away_the_readings_and_sessions(people):
    async with signed_in(people["prof"]) as prof:
        r = await prof.delete(f"/instructor/classes/{people['class']}/students/{people['stu']}")
        assert r.status_code == 204
        assert (await prof.get(f"/instructor/classes/{people['class']}")).json()["students"] == []

    async with signed_in(people["stu"]) as stu:
        assert (await stu.get("/readings")).json() == []
        assert (await stu.get(f"/readings/{people['reading']}/sessions")).json() == []
        # not even by a saved link
        assert (await stu.get(f"/sessions/{people['session']}/transcript")).status_code == 404


@pytest.mark.anyio
async def test_deleting_a_class_hides_it_from_everyone(people):
    async with signed_in(people["prof"]) as prof:
        assert (await prof.delete(f"/instructor/classes/{people['class']}")).status_code == 204
        assert (await prof.get("/instructor/classes")).json() == []
        assert (await prof.get(f"/instructor/classes/{people['class']}")).status_code == 404

    async with signed_in(people["stu"]) as stu:
        assert (await stu.get("/readings")).json() == []
    async with signed_in(people["new_stu"]) as new:
        assert (await new.post("/enrolments", json={"join_code": "4KQ2-9TXM"})).status_code == 404


@pytest.mark.anyio
async def test_deleting_keeps_the_sessions_in_the_data(point_app_at_test_db, people):
    """Out of sight for students, but still there for the study."""
    async with signed_in(people["prof"]) as prof:
        await prof.delete(f"/instructor/classes/{people['class']}")

    engine = create_async_engine(point_app_at_test_db)
    async with async_sessionmaker(engine)() as s:
        assert await s.get(Session, people["session"]) is not None
    await engine.dispose()
