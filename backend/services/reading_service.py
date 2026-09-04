"""Reading queries for the reading list and its entry into a session.

Visibility is the point here and an access boundary: a student sees a reading
only if they are enrolled in a class it is assigned to. Every query joins
enrolment -> class -> reading_assignment -> reading and filters the soft-deleted
rows out at each hop, so a reading in another class, an unassigned reading, or a
dropped enrolment never leaks in.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Class,
    CoreComponent,
    Enrolment,
    Reading,
    ReadingAssignment,
    Session,
    SessionStatus,
)


def _visible_readings(user_id: uuid.UUID):
    """A select of (Reading, class name) the student may see. One row per class a
    reading is assigned to that the student is in — usually exactly one."""
    return (
        select(Reading, Class.name.label("class_name"))
        .join(
            ReadingAssignment,
            (ReadingAssignment.reading_id == Reading.id)
            & (ReadingAssignment.deleted_at.is_(None)),
        )
        .join(
            Class,
            (Class.id == ReadingAssignment.class_id) & (Class.deleted_at.is_(None)),
        )
        .join(
            Enrolment,
            (Enrolment.class_id == Class.id)
            & (Enrolment.student_id == user_id)
            & (Enrolment.deleted_at.is_(None)),
        )
        .where(Reading.deleted_at.is_(None))
    )


async def _statuses(
    db: AsyncSession, user_id: uuid.UUID, reading_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """The list status per reading: the student's latest *terminal* session on it.

    In-progress sessions are ignored — they are not resumable and the auto-discard
    flow does not exist yet, so a lingering one must not shadow a real outcome or
    read as anything but 'not started'.
    """
    if not reading_ids:
        return {}
    rows = await db.execute(
        select(Session.reading_id, Session.status, Session.started_at)
        .where(
            Session.student_id == user_id,
            Session.reading_id.in_(reading_ids),
            Session.status.in_(
                [SessionStatus.COMPLETE.value, SessionStatus.FALLBACK.value]
            ),
        )
        .order_by(Session.started_at.desc())
    )
    latest: dict[uuid.UUID, str] = {}
    for reading_id, status, _started in rows:
        # First seen per reading is the most recent, since ordered desc.
        if reading_id not in latest:
            latest[reading_id] = (
                "complete" if SessionStatus(status) is SessionStatus.COMPLETE else "failed"
            )
    return latest


async def list_readings(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    """Every reading the student can see, with its class and status."""
    rows = (await db.execute(_visible_readings(user_id).order_by(Reading.created_at))).all()
    statuses = await _statuses(db, user_id, [r.id for r, _ in rows])
    return [
        {
            "id": reading.id,
            "title": reading.title,
            "description": reading.description,
            "class_name": class_name,
            "status": statuses.get(reading.id, "not_started"),
        }
        for reading, class_name in rows
    ]


async def get_reading_detail(
    db: AsyncSession, user_id: uuid.UUID, reading_id: uuid.UUID
) -> dict | None:
    """One reading the student can see: its text, class and core components.

    Returns None if the reading does not exist or the student cannot see it —
    the router turns that into the same 404, so an unassigned id is
    indistinguishable from a missing one.
    """
    hit = (
        await db.execute(
            _visible_readings(user_id).where(Reading.id == reading_id).limit(1)
        )
    ).first()
    if hit is None:
        return None
    reading, class_name = hit

    components = await db.scalars(
        select(CoreComponent.text)
        .where(CoreComponent.reading_id == reading_id)
        .order_by(CoreComponent.position)
    )
    return {
        "id": reading.id,
        "title": reading.title,
        "description": reading.description,
        "class_name": class_name,
        "content": reading.content,
        "core_components": list(components),
    }
