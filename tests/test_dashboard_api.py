"""The class dashboard: the three statistics, the roster, and who may read a
transcript.

The sessions are built by hand rather than seeded, so the expected numbers are
visible in this file: two students on one reading, one finishing and one running
out of attempts on Elaborate.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.models import (
    Assessment,
    Attempt,
    Class,
    CriterionJudgment,
    Enrolment,
    Reading,
    ReadingAssignment,
    Role,
    SeeiStep,
    Session,
    SessionStatus,
    User,
    Verdict,
    utcnow,
)

pytestmark = pytest.mark.usefixtures("fresh_engine")

STEPS = [SeeiStep.STATE, SeeiStep.ELABORATE, SeeiStep.EXEMPLIFY, SeeiStep.ILLUSTRATE]
#: Same limit the Orchestrator enforces: a third failure ends the session.
ATTEMPT_LIMIT = 3


def build_session(student, reading, plan, days_ago: int):
    """One session and its attempts.

    `plan` is one (attempts, criteria that fail) pair per step reached. A step
    fails its early attempts and passes its last one, unless it used all three
    attempts, which is the fallback: every attempt failed and the session ends.
    """
    started = utcnow() - timedelta(days=days_ago)
    rows = []
    passed_all = True
    last_step = STEPS[0]
    for step, (tries, failing) in zip(STEPS, plan):
        last_step = step
        out_of_attempts = tries >= ATTEMPT_LIMIT
        for n in range(1, tries + 1):
            fails = failing if failing and (n < tries or out_of_attempts) else []
            attempt = Attempt(
                step=step,
                attempt_number=n,
                response_text=f"{step.value} attempt {n}",
                submitted_at=started + timedelta(minutes=n),
            )
            assessment = Assessment(
                verdict=Verdict.FAIL if fails else Verdict.PASS,
                raw_response="[test]",
            )
            rows.append((attempt, assessment, fails))
            if fails and n == tries:
                passed_all = False
        if not passed_all:
            break

    session = Session(
        student_id=student.id,
        reading_id=reading.id,
        status=SessionStatus.COMPLETE if passed_all else SessionStatus.FALLBACK,
        current_step=last_step,
        started_at=started,
        ended_at=started + timedelta(minutes=20),
        rubric_version="v3",
        tutor_prompt_version="v2",
        assessment_prompt_version="v3",
        llm_model="test",
    )
    return session, rows


@pytest.fixture
async def world(point_app_at_test_db):
    """One class, two students, one reading, two finished sessions.

    Mateo passes every step. Bea fails Elaborate three times, which ends her
    session in fallback with only State passed.
    """
    engine = create_async_engine(point_app_at_test_db)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(delete(User))
        await s.commit()

        prof = User(role=Role.INSTRUCTOR, name="Prof", email="prof@dlsu.edu.ph", google_sub="p1")
        other = User(role=Role.INSTRUCTOR, name="Other", email="other@dlsu.edu.ph", google_sub="p2")
        mateo = User(role=Role.STUDENT, name="Mateo", email="mateo@dlsu.edu.ph", google_sub="s1")
        bea = User(role=Role.STUDENT, name="Bea", email="bea@dlsu.edu.ph", google_sub="s2")
        chelsea = User(role=Role.STUDENT, name="Chelsea", email="chelsea@dlsu.edu.ph", google_sub="s3")
        s.add_all([prof, other, mateo, bea, chelsea])
        await s.flush()

        klass = Class(instructor_id=prof.id, name="STRAMA", section="K31", join_code="4KQ2-9TXM")
        elsewhere = Class(instructor_id=prof.id, name="STSWENG", section="S11", join_code="7HWP-3CNE")
        read = Reading(uploaded_by=prof.id, title="Strategy", description="Coordinated actions", content="body")
        unassigned = Reading(uploaded_by=prof.id, title="Business Model", content="body")
        s.add_all([klass, elsewhere, read, unassigned])
        await s.flush()
        s.add_all([
            Enrolment(student_id=mateo.id, class_id=klass.id),
            Enrolment(student_id=bea.id, class_id=klass.id),
            Enrolment(student_id=chelsea.id, class_id=klass.id),
            ReadingAssignment(reading_id=read.id, class_id=klass.id),
            ReadingAssignment(reading_id=unassigned.id, class_id=elsewhere.id),
        ])

        # Mateo: State passes first try, Elaborate on the second, the rest first.
        mateo_session, mateo_rows = build_session(
            mateo, read, [(1, []), (2, ["Completeness"]), (1, []), (1, [])], days_ago=3
        )
        # Bea: State first try, then three failed tries at Elaborate.
        bea_session, bea_rows = build_session(
            bea, read, [(1, []), (3, ["Completeness", "Coherence"])], days_ago=2
        )
        s.add_all([mateo_session, bea_session])
        await s.flush()

        for session, rows in ((mateo_session, mateo_rows), (bea_session, bea_rows)):
            for attempt, assessment, fails in rows:
                attempt.session_id = session.id
                s.add(attempt)
                await s.flush()
                assessment.attempt_id = attempt.id
                s.add(assessment)
                await s.flush()
                s.add_all([
                    CriterionJudgment(assessment_id=assessment.id, criterion=c, passed=False)
                    for c in fails
                ])
        await s.commit()

        ids = {
            "prof": prof.id, "other": other.id,
            "mateo": mateo.id, "bea": bea.id, "chelsea": chelsea.id,
            "class": klass.id, "elsewhere": elsewhere.id,
            "reading": read.id, "unassigned": unassigned.id,
            "mateo_session": mateo_session.id, "bea_session": bea_session.id,
        }
    await engine.dispose()
    return ids


@asynccontextmanager
async def signed_in(user_id):
    from backend.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/auth/dev/login", json={"user_id": str(user_id)})
        assert r.status_code == 200
        yield client


# --------------------------------------------------------------------------- #
# statistics


@pytest.mark.anyio
async def test_the_class_statistics_count_every_finished_session(world):
    async with signed_in(world["prof"]) as prof:
        body = (await prof.get(f"/instructor/classes/{world['class']}/statistics")).json()

    stats = body["statistics"]
    assert stats["session_count"] == 2
    rates = {r["step"]: (r["passed"], r["total"], r["percent"]) for r in stats["pass_rates"]}
    # State: two attempts, both passed. Elaborate: five attempts, one passed.
    assert rates["State"] == (2, 2, 100)
    assert rates["Elaborate"] == (1, 5, 20)
    assert rates["Illustrate"] == (1, 1, 100)

    failures = {c["criterion"]: c["failures"] for c in stats["failed_criteria"]}
    assert failures == {"Completeness": 4, "Coherence": 3}
    assert [c["criterion"] for c in stats["failed_criteria"]][0] == "Completeness"

    averages = {a["step"]: a["average"] for a in stats["average_attempts"]}
    assert averages["State"] == 1.0
    assert averages["Elaborate"] == 2.0  # only Mateo passed it, on his second try

    assert [(r["title"], r["session_count"]) for r in body["readings"]] == [("Strategy", 2)]


@pytest.mark.anyio
async def test_a_class_with_no_sessions_reports_none_rather_than_zeroes(world):
    async with signed_in(world["prof"]) as prof:
        body = (await prof.get(f"/instructor/classes/{world['elsewhere']}/statistics")).json()

    stats = body["statistics"]
    assert stats["session_count"] == 0
    assert (stats["pass_rates"], stats["failed_criteria"], stats["average_attempts"]) == ([], [], [])
    assert [r["session_count"] for r in body["readings"]] == [0]


@pytest.mark.anyio
async def test_reading_statistics_are_the_same_numbers_narrowed(world):
    async with signed_in(world["prof"]) as prof:
        whole = (await prof.get(f"/instructor/classes/{world['class']}/statistics")).json()
        one = (
            await prof.get(
                f"/instructor/classes/{world['class']}/readings/{world['reading']}"
            )
        ).json()

    # The class has one reading with sessions, so the two agree exactly.
    assert one["statistics"] == whole["statistics"]
    assert (one["title"], one["class_label"]) == ("Strategy", "STRAMA K31")


# --------------------------------------------------------------------------- #
# the roster


@pytest.mark.anyio
async def test_the_roster_says_how_far_each_student_got(world):
    async with signed_in(world["prof"]) as prof:
        body = (
            await prof.get(
                f"/instructor/classes/{world['class']}/readings/{world['reading']}"
            )
        ).json()

    rows = {s["name"]: s for s in body["students"]}
    assert [s["name"] for s in body["students"]] == ["Bea", "Chelsea", "Mateo"]

    assert rows["Mateo"]["status"] == "completed"
    assert rows["Mateo"]["steps_passed"] == 4
    assert rows["Mateo"]["stopped_on"] is None
    assert rows["Mateo"]["session_id"] == str(world["mateo_session"])

    # The flag: out of attempts on Elaborate, with only State behind her.
    assert rows["Bea"]["status"] == "stopped_early"
    assert rows["Bea"]["stopped_on"] == "Elaborate"
    assert rows["Bea"]["steps_passed"] == 1

    assert rows["Chelsea"]["status"] == "not_started"
    assert rows["Chelsea"]["session_id"] is None
    assert rows["Chelsea"]["last_session_at"] is None


# --------------------------------------------------------------------------- #
# who may look


@pytest.mark.anyio
async def test_a_reading_outside_this_class_is_not_found(world):
    async with signed_in(world["prof"]) as prof:
        r = await prof.get(
            f"/instructor/classes/{world['class']}/readings/{world['unassigned']}"
        )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_another_instructors_class_is_not_found_and_students_are_refused(world):
    async with signed_in(world["other"]) as other:
        assert (await other.get(f"/instructor/classes/{world['class']}/statistics")).status_code == 404
        assert (
            await other.get(
                f"/instructor/classes/{world['class']}/readings/{world['reading']}"
            )
        ).status_code == 404
    async with signed_in(world["mateo"]) as student:
        assert (await student.get(f"/instructor/classes/{world['class']}/statistics")).status_code == 403


@pytest.mark.anyio
async def test_the_instructor_can_read_their_students_transcript(world):
    async with signed_in(world["prof"]) as prof:
        r = await prof.get(f"/sessions/{world['bea_session']}/transcript")
    assert r.status_code == 200
    body = r.json()
    assert body["student_name"] == "Bea"
    assert body["reading_title"] == "Strategy"
    assert body["class_name"] == "STRAMA K31"
    assert [s["step"] for s in body["steps"]] == ["State", "Elaborate"]


@pytest.mark.anyio
async def test_a_transcript_stays_closed_to_everyone_else(world):
    async with signed_in(world["other"]) as other:
        assert (await other.get(f"/sessions/{world['bea_session']}/transcript")).status_code == 404
    async with signed_in(world["mateo"]) as classmate:
        assert (await classmate.get(f"/sessions/{world['bea_session']}/transcript")).status_code == 404
    async with signed_in(world["bea"]) as bea:
        assert (await bea.get(f"/sessions/{world['bea_session']}/transcript")).status_code == 200
