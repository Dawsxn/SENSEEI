"""What an instructor sees about a class: the three statistics, and the roster.

`docs/context/data-model.md` §4.3.6 specifies three statistics, class-wide and
narrowable to one reading: the pass rate for each SEE-I step, the most-failed
criteria, and the average attempts needed to pass each step. All three are
computed here over the same set of sessions, so the class view and the reading
view can never disagree about what they are counting.

**Which sessions count.** Those by a student enrolled in this class, on a reading
assigned to this class, that finished. In-progress ones are left out: they are
not resumable, and an abandoned one would sit in the numbers forever.

A student enrolled in two classes that both use a reading has their session
counted in both, which is right: each class's numbers describe that class.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    FINISHED_STATUSES,
    STEP_ORDER,
    Assessment,
    Attempt,
    Class,
    CriterionJudgment,
    Enrolment,
    Reading,
    ReadingAssignment,
    SeeiStep,
    Session,
    SessionStatus,
    User,
    Verdict,
)
from .class_service import ClassNotFound, _owned

#: How many criteria the "most failed" list shows. Long enough to see a pattern,
#: short enough to read at a glance.
TOP_CRITERIA = 5

FINISHED = FINISHED_STATUSES


class ReadingNotInClass(Exception):
    """No such reading, or it is not assigned to this class."""


@dataclass
class Scope:
    """The sessions a set of statistics is computed over."""

    class_id: uuid.UUID
    reading_id: uuid.UUID | None = None


def _sessions(scope: Scope):
    """A select of the session ids in scope."""
    q = (
        select(Session.id)
        .join(
            Enrolment,
            (Enrolment.student_id == Session.student_id)
            & (Enrolment.class_id == scope.class_id)
            & (Enrolment.deleted_at.is_(None)),
        )
        .join(
            ReadingAssignment,
            (ReadingAssignment.reading_id == Session.reading_id)
            & (ReadingAssignment.class_id == scope.class_id)
            & (ReadingAssignment.deleted_at.is_(None)),
        )
        .join(
            Reading,
            (Reading.id == Session.reading_id) & (Reading.deleted_at.is_(None)),
        )
        .where(Session.status.in_(FINISHED))
    )
    if scope.reading_id is not None:
        q = q.where(Session.reading_id == scope.reading_id)
    return q


async def statistics(db: AsyncSession, scope: Scope) -> dict:
    """The three statistics over one scope, plus how many sessions they cover.

    A step nobody has reached is absent from the pass-rate and attempts lists
    rather than reported as zero: no data and a rate of zero are different
    things, and only one of them is bad news.
    """
    sessions = _sessions(scope).subquery()
    in_scope = Attempt.session_id.in_(select(sessions.c.id))

    graded = (
        await db.execute(
            select(
                Attempt.step,
                func.count().label("total"),
                func.count()
                .filter(Assessment.verdict == Verdict.PASS.value)
                .label("passed"),
                func.avg(Attempt.attempt_number)
                .filter(Assessment.verdict == Verdict.PASS.value)
                .label("avg_attempts"),
            )
            .join(Assessment, Assessment.attempt_id == Attempt.id)
            .where(in_scope)
            .group_by(Attempt.step)
        )
    ).all()
    by_step = {
        SeeiStep(step): (total, passed, avg_attempts)
        for step, total, passed, avg_attempts in graded
    }

    # Counted per step, not per name: several steps have a criterion with the
    # same name (Completeness, Accuracy), and each means something different.
    failures = (
        await db.execute(
            select(Attempt.step, CriterionJudgment.criterion, func.count().label("failures"))
            .join(Assessment, Assessment.id == CriterionJudgment.assessment_id)
            .join(Attempt, Attempt.id == Assessment.attempt_id)
            .where(in_scope, CriterionJudgment.passed.is_(False))
            .group_by(Attempt.step, CriterionJudgment.criterion)
            .order_by(func.count().desc(), Attempt.step, CriterionJudgment.criterion)
            .limit(TOP_CRITERIA)
        )
    ).all()

    session_count = await db.scalar(
        select(func.count()).select_from(_sessions(scope).subquery())
    )

    pass_rates, attempts = [], []
    for step in STEP_ORDER:
        row = by_step.get(step)
        if row is None:
            continue
        total, passed, avg_attempts = row
        pass_rates.append(
            {"step": step.value, "passed": passed, "total": total,
             "percent": round(passed * 100 / total)}
        )
        if avg_attempts is not None:
            attempts.append(
                {"step": step.value, "average": round(float(avg_attempts), 1)}
            )

    return {
        "session_count": session_count or 0,
        "pass_rates": pass_rates,
        "failed_criteria": [
            {"step": SeeiStep(step).value, "criterion": c, "failures": n}
            for step, c, n in failures
        ],
        "average_attempts": attempts,
    }


async def class_dashboard(
    db: AsyncSession, instructor_id: uuid.UUID, class_id: uuid.UUID
) -> dict:
    """The class page's numbers: statistics across every reading assigned to it,
    and those readings with a session count each. Raises ClassNotFound if the
    class is not this instructor's."""
    await _owned(db, instructor_id, class_id)
    flagged = _flagged(await _latest_sessions(db, class_id))
    return {
        "statistics": await statistics(db, Scope(class_id)),
        "readings": await _readings_with_counts(db, class_id, flagged),
        # A student is flagged in the class if they are on any of its readings.
        "flagged_student_ids": sorted({s.student_id for s in flagged}, key=str),
    }


async def reading_in_class(
    db: AsyncSession,
    instructor_id: uuid.UUID,
    class_id: uuid.UUID,
    reading_id: uuid.UUID,
) -> dict:
    """One reading inside one class: its statistics and the class roster.

    The pairing is the point. A reading's numbers only mean something for the
    class that read it, and a student's progress is progress on this reading.
    """
    klass = await _owned(db, instructor_id, class_id)
    reading = await db.scalar(
        select(Reading)
        .join(
            ReadingAssignment,
            (ReadingAssignment.reading_id == Reading.id)
            & (ReadingAssignment.class_id == class_id)
            & (ReadingAssignment.deleted_at.is_(None)),
        )
        .where(Reading.id == reading_id, Reading.deleted_at.is_(None))
    )
    if reading is None:
        raise ReadingNotInClass

    return {
        "id": reading.id,
        "title": reading.title,
        "description": reading.description,
        "class_id": klass.id,
        "class_label": f"{klass.name} {klass.section}".strip(),
        "statistics": await statistics(db, Scope(class_id, reading_id)),
        "students": await roster(db, class_id, reading_id),
    }


async def roster(
    db: AsyncSession, class_id: uuid.UUID, reading_id: uuid.UUID
) -> list[dict]:
    """Every student in the class, and how far they got on this reading.

    Their latest finished session, since that is the one an instructor would act
    on. Earlier attempts still count in the statistics; only the roster picks one.
    """
    students = (
        await db.execute(
            select(User)
            .join(Enrolment, Enrolment.student_id == User.id)
            .where(Enrolment.class_id == class_id, Enrolment.deleted_at.is_(None))
            .order_by(func.lower(User.name))
        )
    ).scalars().all()
    if not students:
        return []

    latest = await _latest_sessions(db, class_id, reading_id=reading_id)
    sessions = {s.student_id: s for s in latest}
    passed = await _passed_steps(db, latest)
    return [
        {
            "id": student.id,
            "name": student.name,
            "email": student.email,
            **_progress(sessions.get(student.id), passed),
        }
        for student in students
    ]


async def _latest_sessions(
    db: AsyncSession,
    class_id: uuid.UUID,
    *,
    reading_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
) -> list[Session]:
    """Each student's latest finished session on each reading, in this class.

    The one an instructor acts on, and the one that decides a flag: a student is
    flagged on a reading while their latest session there ran out of tries, and
    is no longer once a later one passes. DISTINCT ON keeps one row per student
    and reading: the newest, by the ordering below.
    """
    q = select(Session).where(Session.id.in_(_sessions(Scope(class_id, reading_id))))
    if student_id is not None:
        q = q.where(Session.student_id == student_id)
    q = q.order_by(
        Session.student_id, Session.reading_id, Session.started_at.desc()
    ).distinct(Session.student_id, Session.reading_id)
    return list((await db.execute(q)).scalars().all())


async def _passed_steps(db: AsyncSession, sessions: list[Session]) -> dict:
    """How many distinct steps each of these sessions passed."""
    if not sessions:
        return {}
    return dict(
        (
            await db.execute(
                select(Attempt.session_id, func.count(func.distinct(Attempt.step)))
                .join(Assessment, Assessment.attempt_id == Attempt.id)
                .where(
                    Attempt.session_id.in_([s.id for s in sessions]),
                    Assessment.verdict == Verdict.PASS.value,
                )
                .group_by(Attempt.session_id)
            )
        ).all()
    )


def _progress(sess: Session | None, passed: dict) -> dict:
    """Where a student got to on one reading, from their latest finished session."""
    ended = SessionStatus(sess.status) if sess is not None else None
    # Out of attempts, or (trial mode) out of time: either way they stopped
    # short of Illustrate, on a step that matters to whoever reads this.
    stopped = ended in (SessionStatus.FALLBACK, SessionStatus.TIMED_OUT)
    return {
        "session_id": sess.id if sess else None,
        "status": (
            "not_started" if sess is None
            else "stopped_early" if ended is SessionStatus.FALLBACK
            else "timed_out" if ended is SessionStatus.TIMED_OUT
            else "completed"
        ),
        "steps_passed": passed.get(sess.id, 0) if sess else 0,
        # The step they stopped on, which is where the instructor's attention
        # belongs.
        "stopped_on": SeeiStep(sess.current_step).value if stopped else None,
        "last_session_at": (sess.ended_at or sess.started_at) if sess else None,
    }


def _flagged(sessions: list[Session]) -> list[Session]:
    """The latest sessions that raise a flag: they ran out of tries."""
    return [s for s in sessions if SessionStatus(s.status) is SessionStatus.FALLBACK]


async def _readings_with_counts(
    db: AsyncSession, class_id: uuid.UUID, flagged: list[Session]
) -> list[dict]:
    """The class's readings with how many finished sessions each has, and how
    many students are flagged on each, for the class page's readings tab."""
    flags: dict[uuid.UUID, int] = {}
    for sess in flagged:
        flags[sess.reading_id] = flags.get(sess.reading_id, 0) + 1
    counts = dict(
        (
            await db.execute(
                select(Session.reading_id, func.count())
                .where(Session.id.in_(_sessions(Scope(class_id))))
                .group_by(Session.reading_id)
            )
        ).all()
    )
    readings = await db.scalars(
        select(Reading)
        .join(
            ReadingAssignment,
            (ReadingAssignment.reading_id == Reading.id)
            & (ReadingAssignment.class_id == class_id)
            & (ReadingAssignment.deleted_at.is_(None)),
        )
        .where(Reading.deleted_at.is_(None))
        .order_by(Reading.created_at)
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "session_count": counts.get(r.id, 0),
            "flagged_count": flags.get(r.id, 0),
        }
        for r in readings
    ]


class StudentNotInClass(Exception):
    """No such student in this class."""


async def _enrolled(db: AsyncSession, class_id: uuid.UUID, student_id: uuid.UUID):
    hit = (
        await db.execute(
            select(User, Enrolment.enrolled_at)
            .join(Enrolment, Enrolment.student_id == User.id)
            .where(
                Enrolment.class_id == class_id,
                Enrolment.student_id == student_id,
                Enrolment.deleted_at.is_(None),
            )
        )
    ).first()
    if hit is None:
        raise StudentNotInClass
    return hit


async def _assigned_readings(db: AsyncSession, class_id: uuid.UUID) -> list[Reading]:
    return list(
        await db.scalars(
            select(Reading)
            .join(
                ReadingAssignment,
                (ReadingAssignment.reading_id == Reading.id)
                & (ReadingAssignment.class_id == class_id)
                & (ReadingAssignment.deleted_at.is_(None)),
            )
            .where(Reading.deleted_at.is_(None))
            .order_by(Reading.created_at)
        )
    )


async def student_in_class(
    db: AsyncSession,
    instructor_id: uuid.UUID,
    class_id: uuid.UUID,
    student_id: uuid.UUID,
) -> dict:
    """One student in one class, and how far they got on each of its readings:
    a reading's roster turned the other way."""
    klass = await _owned(db, instructor_id, class_id)
    student, enrolled_at = await _enrolled(db, class_id, student_id)
    latest = await _latest_sessions(db, class_id, student_id=student_id)
    sessions = {s.reading_id: s for s in latest}
    passed = await _passed_steps(db, latest)
    return {
        "id": student.id,
        "name": student.name,
        "email": student.email,
        "enrolled_at": enrolled_at,
        "class_id": klass.id,
        "class_label": f"{klass.name} {klass.section}".strip(),
        "readings": [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                **_progress(sessions.get(r.id), passed),
            }
            for r in await _assigned_readings(db, class_id)
        ],
    }


async def student_sessions(
    db: AsyncSession,
    instructor_id: uuid.UUID,
    class_id: uuid.UUID,
    reading_id: uuid.UUID,
    student_id: uuid.UUID,
) -> dict:
    """Every finished session one student has on one reading, newest first.

    Numbered as the review numbers them (Attempt 1 is the oldest), so the list
    and the session it opens agree. A flagged one stays flagged here after a
    later one passes: the flag on the roster clears, the history does not.
    """
    klass = await _owned(db, instructor_id, class_id)
    reading = next((r for r in await _assigned_readings(db, class_id) if r.id == reading_id), None)
    if reading is None:
        raise ReadingNotInClass
    student, _ = await _enrolled(db, class_id, student_id)
    rows = list(
        await db.scalars(
            select(Session)
            .where(
                Session.student_id == student_id,
                Session.reading_id == reading_id,
                Session.status.in_(FINISHED),
            )
            .order_by(Session.started_at)
        )
    )
    return {
        "id": student.id,
        "name": student.name,
        "email": student.email,
        "class_id": klass.id,
        "class_label": f"{klass.name} {klass.section}".strip(),
        "reading_id": reading.id,
        "reading_title": reading.title,
        "sessions": [
            {
                "id": s.id,
                "index": i,
                "status": SessionStatus(s.status).value,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
            }
            for i, s in reversed(list(enumerate(rows, start=1)))
        ],
    }


__all__ = [
    "ClassNotFound",
    "ReadingNotInClass",
    "StudentNotInClass",
    "Scope",
    "class_dashboard",
    "reading_in_class",
    "roster",
    "statistics",
]
