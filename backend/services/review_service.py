"""Read-only views of finished (or abandoned) sessions.

The reads behind the reading detail dialog and the session review screen.

Two people may open a transcript, by two different rules. A student may open
their own, and only while they can still see the reading. An instructor may open
one of their students': the reading must be assigned to a class they own, and the
student must be enrolled in it. Neither rule lets anyone else in, and a session
that fails both is reported as missing.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    STEP_ORDER,
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
    class_label,
)
from .reading_service import _visible_readings


async def _can_see(
    db: AsyncSession, user_id: uuid.UUID, reading_id: uuid.UUID
) -> bool:
    hit = await db.execute(
        _visible_readings(user_id).where(Reading.id == reading_id).limit(1)
    )
    return hit.first() is not None


async def list_sessions_for_reading(
    db: AsyncSession, user_id: uuid.UUID, reading_id: uuid.UUID
) -> list[dict]:
    """The student's sessions on one reading, newest first.

    `index` is the 1-based ordinal in the order they were taken, so the newest
    session on a reading tried three times is "Attempt 3". It is the student's
    own data, so ownership is the only scope.

    Only finished sessions are listed. An in-progress session is not resumable
    and is discarded when the student leaves (the discard flow is not built yet,
    so abandoned ones linger); listing them would contradict the reading list,
    which counts a reading with only an abandoned session as "not started".

    Empty when the student can no longer see the reading: removed from the class,
    or the class deleted. The sessions stay in the database for the study, but
    the student has lost access to them, as the removal dialog says.
    """
    if not await _can_see(db, user_id, reading_id):
        return []

    sessions = list(
        await db.scalars(
            select(Session)
            .where(
                Session.student_id == user_id,
                Session.reading_id == reading_id,
                Session.status.in_(
                    [SessionStatus.COMPLETE.value, SessionStatus.FALLBACK.value]
                ),
            )
            .order_by(Session.started_at)
        )
    )
    if not sessions:
        return []

    counts = dict(
        (
            await db.execute(
                select(Attempt.session_id, func.count())
                .where(Attempt.session_id.in_([s.id for s in sessions]))
                .group_by(Attempt.session_id)
            )
        ).all()
    )

    out = [
        {
            "id": s.id,
            "index": index,
            "status": SessionStatus(s.status).value,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "attempt_count": counts.get(s.id, 0),
        }
        for index, s in enumerate(sessions, start=1)
    ]
    out.reverse()  # newest first, as the dialog and the attempt selector show it
    return out


async def _instructor_header(
    db: AsyncSession, instructor_id: uuid.UUID, sess: Session
) -> tuple[str, str] | None:
    """The reading's title and class label, if this instructor may see the
    session: their class, holding both the reading and the student."""
    hit = (
        await db.execute(
            select(Reading.title, class_label())
            .join(
                ReadingAssignment,
                (ReadingAssignment.reading_id == Reading.id)
                & (ReadingAssignment.deleted_at.is_(None)),
            )
            .join(
                Class,
                (Class.id == ReadingAssignment.class_id)
                & (Class.instructor_id == instructor_id)
                & (Class.deleted_at.is_(None)),
            )
            .join(
                Enrolment,
                (Enrolment.class_id == Class.id)
                & (Enrolment.student_id == sess.student_id)
                & (Enrolment.deleted_at.is_(None)),
            )
            .where(Reading.id == sess.reading_id, Reading.deleted_at.is_(None))
            .limit(1)
        )
    ).first()
    return None if hit is None else (hit[0], hit[1])


async def get_transcript(
    db: AsyncSession, viewer: User, session_id: uuid.UUID
) -> dict | None:
    """One session's read-only replay: a per-step summary and the full timeline.

    The timeline interleaves the Tutor's messages with the student's responses,
    in the order they happened, so the review reads back exactly as the session
    played. Returns None if the session is missing or the viewer may not see it.
    """
    sess = await db.scalar(select(Session).where(Session.id == session_id))
    if sess is None:
        return None

    instructor = viewer.role == Role.INSTRUCTOR
    if instructor:
        header = await _instructor_header(db, viewer.id, sess)
        if header is None:
            return None
        reading_title, class_name = header
    else:
        if sess.student_id != viewer.id:
            return None
        # A reading the student can no longer see means a session they can no
        # longer open, even by a saved link: removed from the class means removed.
        hit = (
            await db.execute(
                _visible_readings(viewer.id)
                .where(Reading.id == sess.reading_id)
                .limit(1)
            )
        ).first()
        if hit is None:
            return None
        reading_title, class_name = hit[0].title, hit[1]

    # Which attempt this is: its 1-based order among that student's sessions on
    # this reading.
    index = await db.scalar(
        select(func.count())
        .select_from(Session)
        .where(
            Session.student_id == sess.student_id,
            Session.reading_id == sess.reading_id,
            Session.status.in_(
                [SessionStatus.COMPLETE.value, SessionStatus.FALLBACK.value]
            ),
            Session.started_at <= sess.started_at,
        )
    )
    student_name = await db.scalar(select(User.name).where(User.id == sess.student_id))

    attempts = (
        await db.execute(
            select(Attempt, Assessment.verdict)
            .outerjoin(Assessment, Assessment.attempt_id == Attempt.id)
            .where(Attempt.session_id == session_id)
            .order_by(Attempt.submitted_at)
        )
    ).all()

    # per-step summary, in SEE-I order, for the steps the session actually reached
    steps = []
    for step in STEP_ORDER:
        rows = [(a, v) for a, v in attempts if SeeiStep(a.step) is step]
        if not rows:
            continue
        steps.append(
            {
                "step": step.value,
                "attempts": len(rows),
                "passed": any(v == Verdict.PASS.value for _, v in rows),
            }
        )

    messages = await db.scalars(
        select(TutorMessage)
        .where(TutorMessage.session_id == session_id)
        .order_by(TutorMessage.created_at)
    )

    timeline: list[dict] = []
    for m in messages:
        fallback = (m.moves or []) == ["Fallback"]
        timeline.append(
            {
                "role": "fallback" if fallback else "tutor",
                "step": SeeiStep(m.step).value,
                "content": m.content,
                "attempt_number": None,
                "at": m.created_at,
            }
        )
    for attempt, _verdict in attempts:
        timeline.append(
            {
                "role": "student",
                "step": SeeiStep(attempt.step).value,
                "content": attempt.response_text,
                "attempt_number": attempt.attempt_number,
                "at": attempt.submitted_at,
            }
        )
    timeline.sort(key=lambda e: e["at"])

    return {
        "id": sess.id,
        "reading_id": sess.reading_id,
        "reading_title": reading_title,
        "class_name": class_name,
        "student_name": student_name,
        "index": index or 1,
        "status": SessionStatus(sess.status).value,
        "started_at": sess.started_at,
        "ended_at": sess.ended_at,
        "steps": steps,
        "timeline": timeline,
    }
