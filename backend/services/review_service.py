"""Read-only views of finished (or abandoned) sessions.

Two reads behind the reading detail dialog and the session review screen. Both
are scoped to the signed-in student by ownership: a student can list and replay
only their own sessions.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    STEP_ORDER,
    Assessment,
    Attempt,
    Reading,
    SeeiStep,
    Session,
    SessionStatus,
    TutorMessage,
    Verdict,
)
from .reading_service import _visible_readings


async def list_sessions_for_reading(
    db: AsyncSession, user_id: uuid.UUID, reading_id: uuid.UUID
) -> list[dict]:
    """The student's sessions on one reading, newest first.

    `index` is the 1-based ordinal in the order they were taken, so the newest
    session on a reading tried three times is "Attempt 3". It is the student's
    own data, so ownership is the only scope.
    """
    sessions = list(
        await db.scalars(
            select(Session)
            .where(Session.student_id == user_id, Session.reading_id == reading_id)
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


async def get_transcript(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> dict | None:
    """One session's read-only replay: a per-step summary and the full timeline.

    The timeline interleaves the Tutor's messages with the student's responses,
    in the order they happened, so the review reads back exactly as the session
    played. Returns None if the session is missing or not the student's.
    """
    sess = await db.scalar(
        select(Session).where(
            Session.id == session_id, Session.student_id == user_id
        )
    )
    if sess is None:
        return None

    # Reading title and class for the header, and which attempt this is (its
    # 1-based order among the student's sessions on this reading).
    hit = (
        await db.execute(
            _visible_readings(user_id).where(Reading.id == sess.reading_id).limit(1)
        )
    ).first()
    reading_title = hit[0].title if hit else ""
    class_name = hit[1] if hit else ""
    index = await db.scalar(
        select(func.count())
        .select_from(Session)
        .where(
            Session.student_id == user_id,
            Session.reading_id == sess.reading_id,
            Session.started_at <= sess.started_at,
        )
    )

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
        "index": index or 1,
        "status": SessionStatus(sess.status).value,
        "started_at": sess.started_at,
        "ended_at": sess.ended_at,
        "steps": steps,
        "timeline": timeline,
    }
