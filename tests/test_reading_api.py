"""The reading API, against the test database.

The scenario is built to exercise the visibility boundary: a student enrolled in
one class must see the readings assigned to it and, crucially, must not see a
reading assigned only to a class they are not in. Status derivation and the
detail 404 are checked on the same fixture.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.models import (
    Class,
    CoreComponent,
    Enrolment,
    Reading,
    ReadingAssignment,
    Session,
    SessionStatus,
    User,
    Role,
    SeeiStep,
    utcnow,
)

pytestmark = pytest.mark.usefixtures("fresh_engine")


def make_client() -> AsyncClient:
    from backend.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _session(student_id, reading_id, status, days_ago):
    from datetime import timedelta

    started = utcnow() - timedelta(days=days_ago)
    return Session(
        student_id=student_id,
        reading_id=reading_id,
        status=status,
        current_step=SeeiStep.STATE,
        started_at=started,
        ended_at=None if status is SessionStatus.IN_PROGRESS else started,
        rubric_version="v3",
        tutor_prompt_version="v1",
        assessment_prompt_version="v3",
        llm_model="test",
    )


@pytest.fixture
async def world(point_app_at_test_db):
    """A student in class A only, and readings spread across A and B.

    Returns the ids the tests assert on. The signed-in user resolves to this
    student because it carries the stub's google_sub.
    """
    engine = create_async_engine(point_app_at_test_db)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(delete(User))
        await s.commit()

        instructor = User(role=Role.INSTRUCTOR, name="I", email="i@dlsu.edu.ph", google_sub="seed-instructor-1")
        student = User(role=Role.STUDENT, name="S", email="s@dlsu.edu.ph", google_sub="seed-student-1")
        s.add_all([instructor, student])
        await s.flush()

        class_a = Class(instructor_id=instructor.id, name="STRAMA K31", join_code="AAA-1")
        class_b = Class(instructor_id=instructor.id, name="BUSANA S15", join_code="BBB-1")
        s.add_all([class_a, class_b])
        await s.flush()

        # the student is in A only
        s.add(Enrolment(student_id=student.id, class_id=class_a.id))

        def reading(title, desc):
            return Reading(uploaded_by=instructor.id, title=title, description=desc, content=f"{title} body")

        r_done = reading("Strategy", "Coordinated actions to outperform rivals")   # A, completed
        r_new = reading("Business Model", "Customer value, profit formula")        # A, never started
        r_failed = reading("Cognitive Offloading", None)                           # A, fallback
        r_progress = reading("Framing", None)                                      # A, in progress only
        r_other = reading("Strategic Vision", "Direction, market position")        # B only — invisible
        s.add_all([r_done, r_new, r_failed, r_progress, r_other])
        await s.flush()

        s.add(CoreComponent(reading_id=r_done.id, text="a coordinated set of actions", position=0))
        s.add_all([
            ReadingAssignment(reading_id=r_done.id, class_id=class_a.id),
            ReadingAssignment(reading_id=r_new.id, class_id=class_a.id),
            ReadingAssignment(reading_id=r_failed.id, class_id=class_a.id),
            ReadingAssignment(reading_id=r_progress.id, class_id=class_a.id),
            ReadingAssignment(reading_id=r_other.id, class_id=class_b.id),
        ])
        await s.flush()

        s.add_all([
            _session(student.id, r_done.id, SessionStatus.COMPLETE, days_ago=3),
            _session(student.id, r_failed.id, SessionStatus.FALLBACK, days_ago=2),
            _session(student.id, r_progress.id, SessionStatus.IN_PROGRESS, days_ago=1),
        ])
        await s.commit()

        ids = {
            "done": r_done.id, "new": r_new.id, "failed": r_failed.id,
            "progress": r_progress.id, "other": r_other.id,
        }
    await engine.dispose()
    return ids


# --------------------------------------------------------------------------- #


@pytest.mark.anyio
async def test_list_shows_only_readings_the_student_can_see(world):
    async with make_client() as client:
        rows = (await client.get("/readings")).json()

    by_id = {r["id"]: r for r in rows}
    # the four class-A readings are present; the class-B one is not
    assert str(world["other"]) not in by_id
    assert {str(world["done"]), str(world["new"]), str(world["failed"]),
            str(world["progress"])} <= set(by_id)


@pytest.mark.anyio
async def test_status_comes_from_the_latest_terminal_session(world):
    async with make_client() as client:
        by_id = {r["id"]: r for r in (await client.get("/readings")).json()}

    assert by_id[str(world["done"])]["status"] == "complete"
    assert by_id[str(world["new"])]["status"] == "not_started"
    assert by_id[str(world["failed"])]["status"] == "failed"
    # an in-progress session is not resumable, so it reads as not started
    assert by_id[str(world["progress"])]["status"] == "not_started"


@pytest.mark.anyio
async def test_list_carries_class_and_description(world):
    async with make_client() as client:
        by_id = {r["id"]: r for r in (await client.get("/readings")).json()}

    done = by_id[str(world["done"])]
    assert done["class_name"] == "STRAMA K31"
    assert done["description"] == "Coordinated actions to outperform rivals"
    assert by_id[str(world["failed"])]["description"] is None


@pytest.mark.anyio
async def test_detail_returns_content_and_core_components(world):
    async with make_client() as client:
        detail = (await client.get(f"/readings/{world['done']}")).json()

    assert detail["title"] == "Strategy"
    assert detail["class_name"] == "STRAMA K31"
    assert "body" in detail["content"]
    assert detail["core_components"] == ["a coordinated set of actions"]


@pytest.mark.anyio
async def test_detail_of_an_unseen_reading_is_404(world):
    async with make_client() as client:
        # r_other exists but is assigned to a class the student is not in
        r = await client.get(f"/readings/{world['other']}")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_detail_of_a_missing_reading_is_404(world):
    async with make_client() as client:
        r = await client.get(f"/readings/{uuid.uuid4()}")
    assert r.status_code == 404
