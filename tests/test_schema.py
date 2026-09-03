"""The schema holds up the behaviour the app depends on.

These run against a real Postgres, in a separate `senseei_test` database created
on demand, so they never touch whatever you seeded for development. Without a
database they skip, the same way the health test does.

Migrations are applied by Alembic rather than by `SQLModel.metadata.create_all`,
because the migration is what actually ships. A schema that only exists in the
models is a schema nobody deploys.
"""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.models import (
    Assessment,
    Attempt,
    Class,
    CoreComponent,
    CriterionJudgment,
    Enrolment,
    Reading,
    ReadingAssignment,
    Role,
    SeeiStep,
    Session,
    TutorMessage,
    User,
    Verdict,
    utcnow,
)
from backend.settings import get_settings

TEST_DB = "senseei_test"

EXPECTED_TABLES = {
    "app_user",
    "class",
    "enrolment",
    "reading",
    "core_component",
    "reading_assignment",
    "session",
    "attempt",
    "assessment",
    "criterion_judgment",
    "tutor_message",
}


def _swap_database(url: str, name: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{name}"))


async def _create_test_database(admin_url: str) -> None:
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB}
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def database_url() -> str:
    """A migrated `senseei_test`, or skip the module.

    Deliberately a sync fixture. Alembic's command API runs its own event loop
    through migrations/env.py, so keeping this synchronous avoids fighting
    anyio over fixture scope.
    """
    settings = get_settings()
    admin_url = _swap_database(settings.database_url, "senseei")
    test_url = _swap_database(settings.database_url, TEST_DB)

    try:
        asyncio.run(_create_test_database(admin_url))
    except Exception as e:
        pytest.skip(f"no database: {type(e).__name__}. Run: docker compose up -d --wait")

    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", test_url)
    command.upgrade(cfg, "head")
    return test_url


@pytest.fixture
async def db(database_url):
    """A clean database per test, and an engine bound to this test's loop."""
    engine = create_async_engine(database_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        # Users cascade to everything else, so this empties the schema.
        await session.execute(delete(User))
        await session.commit()
        yield session
    await engine.dispose()


# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_migration_creates_every_table(db):
    """`alembic upgrade head` produces the tables the models declare."""
    rows = await db.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    present = {r[0] for r in rows}
    assert EXPECTED_TABLES <= present, EXPECTED_TABLES - present


@pytest.mark.anyio
async def test_soft_delete_frees_the_join_code(db):
    """A deleted class must not hold its join code hostage.

    This is what the partial unique index buys. With a plain unique constraint
    the code would be unusable forever, and nobody would notice until an
    instructor could not create a class.
    """
    instructor = User(
        role=Role.INSTRUCTOR, name="I", email="i@dlsu.edu.ph", google_sub="sub-1"
    )
    db.add(instructor)
    await db.commit()

    first = Class(instructor_id=instructor.id, name="A", join_code="SAME-1")
    db.add(first)
    await db.commit()

    first.deleted_at = utcnow()
    db.add(first)
    await db.commit()

    db.add(Class(instructor_id=instructor.id, name="B", join_code="SAME-1"))
    await db.commit()  # must not raise

    live = await db.scalar(
        select(func.count())
        .select_from(Class)
        .where(Class.join_code == "SAME-1", Class.deleted_at.is_(None))
    )
    assert live == 1


@pytest.mark.anyio
async def test_two_live_classes_cannot_share_a_join_code(db):
    """The index is still unique among rows that are not deleted."""
    instructor = User(
        role=Role.INSTRUCTOR, name="I", email="i@dlsu.edu.ph", google_sub="sub-2"
    )
    db.add(instructor)
    await db.commit()

    db.add(Class(instructor_id=instructor.id, name="A", join_code="DUP-1"))
    await db.commit()

    db.add(Class(instructor_id=instructor.id, name="B", join_code="DUP-1"))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


@pytest.mark.anyio
async def test_attempt_numbers_are_unique_within_a_step(db):
    """Two attempt 1s for the same step would corrupt the attempt statistics."""
    tree = await _one_session(db)
    db.add(
        Attempt(
            session_id=tree["session"].id,
            step=SeeiStep.STATE,
            attempt_number=1,
            response_text="duplicate",
        )
    )
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


@pytest.mark.anyio
async def test_deleting_a_user_purges_their_whole_tree(db):
    """The study rules require a real delete, not a flag.

    A withdrawing participant's record has to go, which means one delete has to
    reach sessions, attempts, assessments, criterion judgments and messages. If
    a foreign key loses its ON DELETE CASCADE, this is what catches it.
    """
    tree = await _one_session(db)

    for model in (Session, Attempt, Assessment, CriterionJudgment, TutorMessage):
        assert await db.scalar(select(func.count()).select_from(model)), model

    await db.execute(delete(User).where(User.id == tree["student"].id))
    await db.commit()

    for model in (Session, Attempt, Assessment, CriterionJudgment, TutorMessage):
        left = await db.scalar(select(func.count()).select_from(model))
        assert left == 0, f"{model.__tablename__} still has {left} rows"


@pytest.mark.anyio
async def test_the_three_dashboard_statistics(db):
    """The three statistics the instructor dashboard needs are real queries.

    Expected values are computed in Python from the inserted objects, so the
    assertion compares two independent routes to the same number rather than
    checking SQL against itself.
    """
    import importlib.util

    from agents.rubric import load_rubric

    load_rubric("agents/rubrics/rubric_v3.yaml")
    spec = importlib.util.spec_from_file_location("seed", "scripts/seed.py")
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)

    rows = seed.build_everything()
    await seed.insert_in_waves(db, rows)
    await db.commit()

    attempts = {a.id: a for a in rows if isinstance(a, Attempt)}
    assessments = [a for a in rows if isinstance(a, Assessment)]
    judgments = [j for j in rows if isinstance(j, CriterionJudgment)]

    # --- pass rate per step ---------------------------------------------
    want_pass = Counter()
    want_total = Counter()
    for assessment in assessments:
        step = attempts[assessment.attempt_id].step.value
        want_total[step] += 1
        if assessment.verdict is Verdict.PASS:
            want_pass[step] += 1

    result = await db.execute(
        select(
            Attempt.step,
            func.count().label("total"),
            func.count().filter(Assessment.verdict == Verdict.PASS.value).label("passed"),
        )
        .join(Assessment, Assessment.attempt_id == Attempt.id)
        .group_by(Attempt.step)
    )
    got = {step: (total, passed) for step, total, passed in result}
    assert got == {s: (want_total[s], want_pass[s]) for s in want_total}

    # --- most frequently failed criteria --------------------------------
    want_failed = Counter(j.criterion for j in judgments if not j.passed)

    result = await db.execute(
        select(CriterionJudgment.criterion, func.count())
        .where(CriterionJudgment.passed.is_(False))
        .group_by(CriterionJudgment.criterion)
    )
    assert dict(result.all()) == dict(want_failed)
    assert want_failed, "the seed produced no failures, so this proves nothing"

    # --- average attempts to pass each step -----------------------------
    tries: dict[str, list[int]] = defaultdict(list)
    for assessment in assessments:
        attempt = attempts[assessment.attempt_id]
        if assessment.verdict is Verdict.PASS:
            tries[attempt.step.value].append(attempt.attempt_number)

    result = await db.execute(
        select(Attempt.step, func.avg(Attempt.attempt_number))
        .join(Assessment, Assessment.attempt_id == Attempt.id)
        .where(Assessment.verdict == Verdict.PASS.value)
        .group_by(Attempt.step)
    )
    for step, avg in result:
        expected = sum(tries[step]) / len(tries[step])
        assert float(avg) == pytest.approx(expected)


# ---------------------------------------------------------------------------


async def _one_session(db):
    """A minimal but complete tree: user through to criterion judgment."""
    instructor = User(
        role=Role.INSTRUCTOR, name="I", email="i@dlsu.edu.ph", google_sub="sub-t-i"
    )
    student = User(
        role=Role.STUDENT, name="S", email="s@dlsu.edu.ph", google_sub="sub-t-s"
    )
    db.add_all([instructor, student])
    await db.commit()

    klass = Class(instructor_id=instructor.id, name="C", join_code="TREE-1")
    reading = Reading(uploaded_by=instructor.id, title="R", content="body")
    db.add_all([klass, reading])
    await db.commit()

    db.add_all(
        [
            Enrolment(student_id=student.id, class_id=klass.id),
            ReadingAssignment(reading_id=reading.id, class_id=klass.id),
            CoreComponent(reading_id=reading.id, text="c", position=0),
        ]
    )

    session = Session(
        student_id=student.id,
        reading_id=reading.id,
        rubric_version="v3",
        tutor_prompt_version="v1",
        assessment_prompt_version="v3",
        llm_model="test",
    )
    db.add(session)
    await db.commit()

    attempt = Attempt(
        session_id=session.id,
        step=SeeiStep.STATE,
        attempt_number=1,
        response_text="an answer",
    )
    db.add(attempt)
    await db.commit()

    assessment = Assessment(attempt_id=attempt.id, verdict=Verdict.FAIL)
    db.add(assessment)
    await db.commit()

    db.add_all(
        [
            CriterionJudgment(
                assessment_id=assessment.id, criterion="Clarity", passed=False,
                reason="vague",
            ),
            TutorMessage(
                session_id=session.id,
                step=SeeiStep.STATE,
                attempt_id=attempt.id,
                moves=["Acknowledgement"],
                content="feedback",
            ),
        ]
    )
    await db.commit()

    return {"instructor": instructor, "student": student, "session": session}
