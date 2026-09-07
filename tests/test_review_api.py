"""The review API: past sessions on a reading, and one session's replay.

A session is built by hand with a known shape — State failed then passed,
Elaborate passed — so the per-step summary and the interleaved timeline can be
asserted exactly. Ownership is checked: a student cannot list or replay another
student's sessions.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.models import (
    Assessment,
    Attempt,
    Class,
    Enrolment,
    Reading,
    ReadingAssignment,
    Role,
    SeeiStep,
    Session,
    SessionStatus,
    TutorMessage,
    User,
    Verdict,
    utcnow,
)

pytestmark = pytest.mark.usefixtures("fresh_engine")


def make_client() -> AsyncClient:
    from backend.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class Clock:
    """Monotonic timestamps, so timeline order is unambiguous."""

    def __init__(self):
        self.t = utcnow()

    def tick(self):
        self.t += timedelta(seconds=30)
        return self.t


def prompt(session, step, content, clock):
    return TutorMessage(
        session_id=session.id, step=step, attempt_id=None,
        moves=["Prompt"], content=content, created_at=clock.tick(),
    )


def tutor_reply(session, step, attempt, moves, content, clock):
    return TutorMessage(
        session_id=session.id, step=step, attempt_id=attempt.id,
        moves=moves, content=content, created_at=clock.tick(),
    )


def attempt_with_verdict(session, step, number, verdict, text, clock):
    a = Attempt(
        session_id=session.id, step=step, attempt_number=number,
        response_text=text, submitted_at=clock.tick(),
    )
    return a, verdict


@pytest.fixture
async def reviewable(point_app_at_test_db):
    """One student with two sessions on a reading, and another student's session
    on the same reading (to prove ownership scoping)."""
    engine = create_async_engine(point_app_at_test_db)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(delete(User))
        await s.commit()

        instructor = User(role=Role.INSTRUCTOR, name="I", email="i@dlsu.edu.ph", google_sub="seed-instructor-1")
        me = User(role=Role.STUDENT, name="Me", email="me@dlsu.edu.ph", google_sub="seed-student-1")
        other = User(role=Role.STUDENT, name="Other", email="o@dlsu.edu.ph", google_sub="seed-student-2")
        s.add_all([instructor, me, other])
        await s.flush()

        klass = Class(instructor_id=instructor.id, name="STRAMA K31", join_code="AAA-1")
        reading = Reading(uploaded_by=instructor.id, title="Strategy", content="body")
        s.add_all([klass, reading])
        await s.flush()
        s.add_all([
            Enrolment(student_id=me.id, class_id=klass.id),
            Enrolment(student_id=other.id, class_id=klass.id),
            ReadingAssignment(reading_id=reading.id, class_id=klass.id),
        ])
        await s.flush()

        def new_session(student, started):
            return Session(
                student_id=student.id, reading_id=reading.id,
                status=SessionStatus.COMPLETE, current_step=SeeiStep.ILLUSTRATE,
                started_at=started, ended_at=started + timedelta(minutes=10),
                rubric_version="v3", tutor_prompt_version="v1",
                assessment_prompt_version="v3", llm_model="test",
            )

        first = new_session(me, utcnow() - timedelta(days=2))
        second = new_session(me, utcnow() - timedelta(days=1))
        theirs = new_session(other, utcnow() - timedelta(days=1))
        # an abandoned, still in-progress session: newest, but must not be listed
        abandoned = new_session(me, utcnow())
        abandoned.status = SessionStatus.IN_PROGRESS
        abandoned.ended_at = None
        s.add_all([first, second, theirs, abandoned])
        await s.flush()

        # first session: a single State attempt that passed
        c1 = Clock()
        rows = [prompt(first, SeeiStep.STATE, "State it.", c1)]
        a1, v1 = attempt_with_verdict(first, SeeiStep.STATE, 1, Verdict.PASS, "a good one", c1)
        rows.append(a1)
        s.add_all(rows)
        await s.flush()
        s.add(Assessment(attempt_id=a1.id, verdict=v1))
        s.add(tutor_reply(first, SeeiStep.STATE, a1, ["Acknowledgement", "Transition"], "Good.", c1))

        # second session: State failed then passed, Elaborate passed
        c2 = Clock()
        second_rows = [prompt(second, SeeiStep.STATE, "State it.", c2)]
        sa1, sv1 = attempt_with_verdict(second, SeeiStep.STATE, 1, Verdict.FAIL, "too vague", c2)
        second_rows.append(sa1)
        s.add_all(second_rows)
        await s.flush()
        s.add(Assessment(attempt_id=sa1.id, verdict=sv1))
        s.add(tutor_reply(second, SeeiStep.STATE, sa1, ["Acknowledgement", "Criterion-Based Feedback", "Re-Prompt"], "Try again.", c2))
        sa2, sv2 = attempt_with_verdict(second, SeeiStep.STATE, 2, Verdict.PASS, "sharper", c2)
        s.add(sa2)
        await s.flush()
        s.add(Assessment(attempt_id=sa2.id, verdict=sv2))
        s.add(tutor_reply(second, SeeiStep.STATE, sa2, ["Acknowledgement", "Transition"], "That completes State.", c2))
        s.add(prompt(second, SeeiStep.ELABORATE, "Now elaborate.", c2))
        ea1, ev1 = attempt_with_verdict(second, SeeiStep.ELABORATE, 1, Verdict.PASS, "expanded", c2)
        s.add(ea1)
        await s.flush()
        s.add(Assessment(attempt_id=ea1.id, verdict=ev1))
        s.add(tutor_reply(second, SeeiStep.ELABORATE, ea1, ["Acknowledgement", "Transition"], "Done.", c2))

        # the other student's session — one attempt, for the ownership checks
        c3 = Clock()
        s.add(prompt(theirs, SeeiStep.STATE, "State it.", c3))
        ta, tv = attempt_with_verdict(theirs, SeeiStep.STATE, 1, Verdict.PASS, "theirs", c3)
        s.add(ta)
        await s.flush()
        s.add(Assessment(attempt_id=ta.id, verdict=tv))

        await s.commit()
        ids = {
            "reading": reading.id, "first": first.id, "second": second.id,
            "theirs": theirs.id,
        }
    await engine.dispose()
    return ids


# --------------------------------------------------------------------------- #


@pytest.mark.anyio
async def test_lists_my_sessions_newest_first(reviewable):
    async with make_client() as client:
        rows = (await client.get(f"/readings/{reviewable['reading']}/sessions")).json()

    # my two finished sessions only — not the other student's, and not my own
    # abandoned in-progress one (newest, but not a real past attempt)
    assert [r["id"] for r in rows] == [str(reviewable["second"]), str(reviewable["first"])]
    # newest first, but indexed in the order taken
    assert [r["index"] for r in rows] == [2, 1]
    by_id = {r["id"]: r for r in rows}
    assert by_id[str(reviewable["second"])]["attempt_count"] == 3
    assert by_id[str(reviewable["first"])]["attempt_count"] == 1


@pytest.mark.anyio
async def test_transcript_summary_and_timeline(reviewable):
    async with make_client() as client:
        t = (await client.get(f"/sessions/{reviewable['second']}/transcript")).json()

    # per-step summary, in SEE-I order
    assert t["steps"] == [
        {"step": "State", "attempts": 2, "passed": True},
        {"step": "Elaborate", "attempts": 1, "passed": True},
    ]
    # the timeline interleaves tutor and student, in order
    roles = [(e["role"], e["step"]) for e in t["timeline"]]
    assert roles == [
        ("tutor", "State"),
        ("student", "State"),
        ("tutor", "State"),
        ("student", "State"),
        ("tutor", "State"),
        ("tutor", "Elaborate"),
        ("student", "Elaborate"),
        ("tutor", "Elaborate"),
    ]
    students = [e for e in t["timeline"] if e["role"] == "student"]
    assert [e["attempt_number"] for e in students] == [1, 2, 1]


@pytest.mark.anyio
async def test_cannot_replay_another_students_session(reviewable):
    async with make_client() as client:
        r = await client.get(f"/sessions/{reviewable['theirs']}/transcript")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_transcript_of_a_missing_session_is_404(reviewable):
    async with make_client() as client:
        r = await client.get(f"/sessions/{uuid.uuid4()}/transcript")
    assert r.status_code == 404
