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

FINISHED = [SessionStatus.COMPLETE.value, SessionStatus.FALLBACK.value]


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

    failures = (
        await db.execute(
            select(CriterionJudgment.criterion, func.count().label("failures"))
            .join(Assessment, Assessment.id == CriterionJudgment.assessment_id)
            .join(Attempt, Attempt.id == Assessment.attempt_id)
            .where(in_scope, CriterionJudgment.passed.is_(False))
            .group_by(CriterionJudgment.criterion)
            .order_by(func.count().desc(), CriterionJudgment.criterion)
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
        "failed_criteria": [{"criterion": c, "failures": n} for c, n in failures],
        "average_attempts": attempts,
    }


async def class_dashboard(
    db: AsyncSession, instructor_id: uuid.UUID, class_id: uuid.UUID
) -> dict:
    """The class page's numbers: statistics across every reading assigned to it,
    and those readings with a session count each. Raises ClassNotFound if the
    class is not this instructor's."""
    await _owned(db, instructor_id, class_id)
    return {
        "statistics": await statistics(db, Scope(class_id)),
        "readings": await _readings_with_counts(db, class_id),
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

    # DISTINCT ON keeps one row per student: the newest, by the ordering below.
    latest = (
        await db.execute(
            select(Session)
            .where(
                Session.student_id.in_([s.id for s in students]),
                Session.reading_id == reading_id,
                Session.status.in_(FINISHED),
            )
            .order_by(Session.student_id, Session.started_at.desc())
            .distinct(Session.student_id)
        )
    ).scalars().all()
    sessions = {s.student_id: s for s in latest}

    passed_steps = dict(
        (
            await db.execute(
                select(Attempt.session_id, func.count(func.distinct(Attempt.step)))
                .join(Assessment, Assessment.attempt_id == Attempt.id)
                .where(
                    Attempt.session_id.in_([s.id for s in latest]),
                    Assessment.verdict == Verdict.PASS.value,
                )
                .group_by(Attempt.session_id)
            )
        ).all()
    )

    out = []
    for student in students:
        sess = sessions.get(student.id)
        stopped = sess is not None and SessionStatus(sess.status) is SessionStatus.FALLBACK
        out.append(
            {
                "id": student.id,
                "name": student.name,
                "email": student.email,
                "session_id": sess.id if sess else None,
                "status": (
                    "not_started" if sess is None
                    else "stopped_early" if stopped
                    else "completed"
                ),
                "steps_passed": passed_steps.get(sess.id, 0) if sess else 0,
                # The step they ran out of attempts on, which is where the
                # instructor's attention belongs.
                "stopped_on": SeeiStep(sess.current_step).value if stopped else None,
                "last_session_at": (sess.ended_at or sess.started_at) if sess else None,
            }
        )
    return out


async def _readings_with_counts(db: AsyncSession, class_id: uuid.UUID) -> list[dict]:
    """The class's readings with how many finished sessions each has, for the
    class page's readings card."""
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
        }
        for r in readings
    ]


__all__ = [
    "ClassNotFound",
    "ReadingNotInClass",
    "Scope",
    "class_dashboard",
    "reading_in_class",
    "roster",
    "statistics",
]
