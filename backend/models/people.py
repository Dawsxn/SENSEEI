"""Users, classes, and who is enrolled in what.

Enrolment is the only thing that decides which readings a student can see.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, String, text
from sqlmodel import Field

from .base import TS, Entity, SoftDelete, utcnow
from .enums import Role


class User(Entity, SoftDelete, table=True):
    """One table for both roles. A user is either a student or an instructor.

    Named `app_user` because `user` is a reserved word in Postgres: the table
    would work only quoted, and every hand-written query in psql would need
    `"user"`.
    """

    __tablename__ = "app_user"
    __table_args__ = (
        # Partial, so a soft-deleted user does not hold their Google identity
        # hostage. Without the WHERE clause they could neither sign back in nor
        # be re-created.
        Index(
            "uq_app_user_google_sub",
            "google_sub",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    role: Role = Field(sa_type=String(16), index=True)
    name: str
    email: str
    google_sub: str = Field(description="Stable subject from Google sign-in")

    #: Null for ordinary users, set for consented study participants. Research
    #: exports substitute this for name and email; the app itself never uses it.
    participant_identifier: str | None = Field(default=None, index=True)

    created_at: datetime = Field(default_factory=utcnow, sa_type=TS)


class Class(Entity, SoftDelete, table=True):
    """A class an instructor owns. Co-teaching is not supported."""

    __tablename__ = "class"
    __table_args__ = (
        Index(
            "uq_class_join_code",
            "join_code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    instructor_id: uuid.UUID = Field(
        foreign_key="app_user.id", ondelete="CASCADE", index=True
    )
    name: str
    join_code: str = Field(description="Generated on creation; students enrol with it")
    created_at: datetime = Field(default_factory=utcnow, sa_type=TS)


class Enrolment(Entity, SoftDelete, table=True):
    """Student in class. The gate on everything a student can see."""

    __tablename__ = "enrolment"
    __table_args__ = (
        Index(
            "uq_enrolment_student_class",
            "student_id",
            "class_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    student_id: uuid.UUID = Field(
        foreign_key="app_user.id", ondelete="CASCADE", index=True
    )
    class_id: uuid.UUID = Field(foreign_key="class.id", ondelete="CASCADE", index=True)
    enrolled_at: datetime = Field(default_factory=utcnow, sa_type=TS)
