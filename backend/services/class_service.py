"""Classes and enrolment: what an instructor manages and how students get in.

Every instructor read and write is scoped to the instructor who owns the class,
and a class that is not theirs is reported exactly as one that does not exist.
Deleting is soft, like everything an instructor manages: the class disappears for
everyone, and the sessions completed in it stay in the database, because they are
the study's results.

Joining is the only thing a student does here, and the join code is the whole of
the access control. An unknown code and a deleted class's code get the same
answer, so codes cannot be probed.
"""

from __future__ import annotations

import re
import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Class,
    Enrolment,
    Reading,
    ReadingAssignment,
    User,
    class_label,
    utcnow,
)

#: No 0/O or 1/I: the code is read aloud in a room and copied off a projector.
CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CODE_HALF = 4
#: How many fresh codes to try before giving up. A collision needs two classes
#: to draw the same one of 32^8 codes, so this is belt and braces.
CODE_ATTEMPTS = 5


class ClassNotFound(Exception):
    """No such class, or not this instructor's. Deliberately the same thing."""


class DuplicateClass(Exception):
    """This instructor already has a class with that name and section."""


class UnknownCode(Exception):
    """No live class has this join code."""


@dataclass
class Fields:
    name: str
    section: str


# --------------------------------------------------------------------------- #
# join codes


def new_join_code() -> str:
    """Eight characters in two halves, `4KQ2-9TXM`."""
    chars = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_HALF * 2))
    return f"{chars[:CODE_HALF]}-{chars[CODE_HALF:]}"


def normalize_code(raw: str) -> str:
    """Accept a code the way people actually type it.

    Lower case, spaces, or a missing hyphen all resolve to the stored form. A
    string that is not eight characters once cleaned is returned upper-cased and
    otherwise untouched, so it simply fails to match.
    """
    cleaned = re.sub(r"[^0-9A-Za-z]", "", raw).upper()
    if len(cleaned) == CODE_HALF * 2:
        return f"{cleaned[:CODE_HALF]}-{cleaned[CODE_HALF:]}"
    return raw.strip().upper()


def _violated(error: IntegrityError, constraint: str) -> bool:
    return constraint in str(error.orig)


# --------------------------------------------------------------------------- #
# instructor: reads


async def _owned(db: AsyncSession, instructor_id: uuid.UUID, class_id: uuid.UUID) -> Class:
    klass = await db.scalar(
        select(Class).where(
            Class.id == class_id,
            Class.instructor_id == instructor_id,
            Class.deleted_at.is_(None),
        )
    )
    if klass is None:
        raise ClassNotFound
    return klass


def _summary(klass: Class) -> dict:
    return {
        "id": klass.id,
        "name": klass.name,
        "section": klass.section,
        "label": f"{klass.name} {klass.section}".strip(),
        "join_code": klass.join_code,
    }


async def list_classes(db: AsyncSession, instructor_id: uuid.UUID) -> list[dict]:
    """The instructor's live classes, with how many students and readings each has."""
    students = (
        select(func.count())
        .select_from(Enrolment)
        .where(Enrolment.class_id == Class.id, Enrolment.deleted_at.is_(None))
        .scalar_subquery()
    )
    readings = (
        select(func.count())
        .select_from(ReadingAssignment)
        .join(Reading, Reading.id == ReadingAssignment.reading_id)
        .where(
            ReadingAssignment.class_id == Class.id,
            ReadingAssignment.deleted_at.is_(None),
            Reading.deleted_at.is_(None),
        )
        .scalar_subquery()
    )
    rows = await db.execute(
        select(Class, students, readings)
        .where(Class.instructor_id == instructor_id, Class.deleted_at.is_(None))
        .order_by(func.lower(Class.name), func.lower(Class.section))
    )
    return [
        {**_summary(klass), "student_count": n_students, "reading_count": n_readings}
        for klass, n_students, n_readings in rows
    ]


async def get_class(
    db: AsyncSession, instructor_id: uuid.UUID, class_id: uuid.UUID
) -> dict:
    """One class with its roster and the readings assigned to it."""
    klass = await _owned(db, instructor_id, class_id)

    roster = await db.execute(
        select(User, Enrolment.enrolled_at)
        .join(Enrolment, Enrolment.student_id == User.id)
        .where(Enrolment.class_id == class_id, Enrolment.deleted_at.is_(None))
        .order_by(Enrolment.enrolled_at, User.name)
    )
    readings = await db.scalars(
        select(Reading)
        .join(ReadingAssignment, ReadingAssignment.reading_id == Reading.id)
        .where(
            ReadingAssignment.class_id == class_id,
            ReadingAssignment.deleted_at.is_(None),
            Reading.deleted_at.is_(None),
        )
        .order_by(Reading.created_at)
    )
    return {
        **_summary(klass),
        "students": [
            {"id": u.id, "name": u.name, "email": u.email, "enrolled_at": at}
            for u, at in roster
        ],
        "readings": [
            {"id": r.id, "title": r.title, "description": r.description}
            for r in readings
        ],
    }


# --------------------------------------------------------------------------- #
# instructor: writes


async def create_class(
    db: AsyncSession, instructor_id: uuid.UUID, fields: Fields
) -> dict:
    """A new class with a fresh join code.

    Two constraints can fire here and they mean different things: a join code
    collision is retried with a new code, a duplicate name and section is the
    instructor's to fix.
    """
    for _ in range(CODE_ATTEMPTS):
        klass = Class(
            instructor_id=instructor_id,
            name=fields.name,
            section=fields.section,
            join_code=new_join_code(),
        )
        db.add(klass)
        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            if _violated(e, "uq_class_name_section"):
                raise DuplicateClass from e
            if _violated(e, "uq_class_join_code"):
                continue
            raise
        return {**_summary(klass), "student_count": 0, "reading_count": 0}
    raise RuntimeError("could not find a free join code")


async def update_class(
    db: AsyncSession, instructor_id: uuid.UUID, class_id: uuid.UUID, fields: Fields
) -> dict:
    klass = await _owned(db, instructor_id, class_id)
    klass.name, klass.section = fields.name, fields.section
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        if _violated(e, "uq_class_name_section"):
            raise DuplicateClass from e
        raise
    return await get_class(db, instructor_id, class_id)


async def delete_class(
    db: AsyncSession, instructor_id: uuid.UUID, class_id: uuid.UUID
) -> None:
    """Soft delete. Students lose its readings; its sessions stay in the data.

    Enrolments and assignments are left as they were: every read already filters
    on the class being live, so there is nothing to cascade, and the history of
    who was in the class survives for the study.
    """
    klass = await _owned(db, instructor_id, class_id)
    klass.deleted_at = utcnow()
    await db.commit()


async def replace_join_code(
    db: AsyncSession, instructor_id: uuid.UUID, class_id: uuid.UUID
) -> dict:
    """Issue a new code. The old one stops working; nobody is unenrolled."""
    klass = await _owned(db, instructor_id, class_id)
    for _ in range(CODE_ATTEMPTS):
        klass.join_code = new_join_code()
        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            if _violated(e, "uq_class_join_code"):
                klass = await _owned(db, instructor_id, class_id)
                continue
            raise
        return _summary(klass)
    raise RuntimeError("could not find a free join code")


async def remove_student(
    db: AsyncSession,
    instructor_id: uuid.UUID,
    class_id: uuid.UUID,
    student_id: uuid.UUID,
) -> None:
    """Soft-delete one enrolment. A student who is not in the class is a 404."""
    await _owned(db, instructor_id, class_id)
    enrolment = await db.scalar(
        select(Enrolment).where(
            Enrolment.class_id == class_id,
            Enrolment.student_id == student_id,
            Enrolment.deleted_at.is_(None),
        )
    )
    if enrolment is None:
        raise ClassNotFound
    enrolment.deleted_at = utcnow()
    await db.commit()


# --------------------------------------------------------------------------- #
# student


async def join_class(db: AsyncSession, student_id: uuid.UUID, raw_code: str) -> dict:
    """Enrol a student by join code.

    Joining a class you are already in succeeds quietly: a double tap or a
    student who forgot they joined should not see an error. A student who was
    removed can rejoin with the code; issuing a new code is how an instructor
    keeps someone out.
    """
    row = (
        await db.execute(
            select(Class, class_label()).where(
                Class.join_code == normalize_code(raw_code),
                Class.deleted_at.is_(None),
            )
        )
    ).first()
    if row is None:
        raise UnknownCode
    klass, label = row

    already = await db.scalar(
        select(Enrolment.id).where(
            Enrolment.class_id == klass.id,
            Enrolment.student_id == student_id,
            Enrolment.deleted_at.is_(None),
        )
    )
    if already is None:
        db.add(Enrolment(student_id=student_id, class_id=klass.id))
        try:
            await db.commit()
        except IntegrityError:
            # Two joins raced; the other one won, which is the same outcome.
            await db.rollback()

    # So the student is told the truth about what just appeared in their list,
    # which for a class made before its readings is nothing.
    reading_count = await db.scalar(
        select(func.count())
        .select_from(ReadingAssignment)
        .join(Reading, Reading.id == ReadingAssignment.reading_id)
        .where(
            ReadingAssignment.class_id == klass.id,
            ReadingAssignment.deleted_at.is_(None),
            Reading.deleted_at.is_(None),
        )
    )
    return {"class_id": klass.id, "label": label, "reading_count": reading_count or 0}
