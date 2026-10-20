"""The trial's participants: IDs made in batches, one batch per sitting.

Only trial mode writes these (docs/context/trial.md). A participant is an
ordinary student `User` underneath, enrolled in the class for their group, so the
tutoring loop, the roster and the statistics need no second path for them. What
this table adds is the sign-in by ID, the batch it belongs to, and the clock.

The app holds no identity for a participant. Their user row's name is their ID
and their email is empty; the only link from an ID to a person is the paper
consent form.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, String
from sqlmodel import Field

from .base import TS, Entity, utcnow


class ParticipantBatch(Entity, table=True):
    """The IDs printed together for one sitting.

    Closing it is what ends the sitting: its IDs stop signing in, and anyone
    still signed in with one is signed out on their next request.
    """

    __tablename__ = "participant_batch"

    instructor_id: uuid.UUID = Field(
        foreign_key="app_user.id", ondelete="CASCADE", index=True
    )
    name: str
    created_at: datetime = Field(default_factory=utcnow, sa_type=TS)
    closed_at: datetime | None = Field(default=None, sa_type=TS)


class Participant(Entity, table=True):
    """One participant ID, and the student it signs in as.

    `position` is the shuffled order the IDs were drawn in, which is the order
    the slips print in. The classes are mixed through it, so a stack of slips
    shows nothing about who goes where.
    """

    __tablename__ = "participant"
    __table_args__ = (Index("uq_participant_code", "code", unique=True),)

    batch_id: uuid.UUID = Field(
        foreign_key="participant_batch.id", ondelete="CASCADE", index=True
    )
    user_id: uuid.UUID = Field(
        foreign_key="app_user.id", ondelete="CASCADE", unique=True, index=True
    )
    class_id: uuid.UUID = Field(foreign_key="class.id", ondelete="CASCADE", index=True)
    #: `P-7K3Q-9TXM`. What the participant types, and all they type.
    code: str = Field(sa_type=String(16))
    position: int

    signed_in_at: datetime | None = Field(default=None, sa_type=TS)
    #: When the reading first opened. Their time runs from here.
    clock_started_at: datetime | None = Field(default=None, sa_type=TS)
    voided_at: datetime | None = Field(default=None, sa_type=TS)
