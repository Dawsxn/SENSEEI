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
from sqlalchemy.dialects.postgresql import JSONB
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
    #: When they pressed Done, in the chatbot and reading-only groups. The
    #: reading-only group's exclusion rule is how soon after the reading opened.
    done_at: datetime | None = Field(default=None, sa_type=TS)


class ChatMessage(Entity, table=True):
    """One message in the chatbot group's conversation, theirs or the model's.

    A reply that failed partway is not stored; the failure is in the event log.
    """

    __tablename__ = "chat_message"

    participant_id: uuid.UUID = Field(
        foreign_key="participant.id", ondelete="CASCADE", index=True
    )
    #: `user` or `assistant`.
    role: str = Field(sa_type=String(16))
    content: str
    created_at: datetime = Field(default_factory=utcnow, sa_type=TS)


class TrialEvent(Entity, table=True):
    """One thing a participant did, for the analysis (docs/context/trial.md).

    `at` is when it happened, by the participant's browser, so a batch sent a
    few seconds late keeps its true order; `received_at` is the server's time.
    `data` carries what each kind needs: which panel, which page, a paste's
    length. Never typed or pasted text.
    """

    __tablename__ = "trial_event"
    __table_args__ = (Index("ix_trial_event_participant_at", "participant_id", "at"),)

    participant_id: uuid.UUID = Field(
        foreign_key="participant.id", ondelete="CASCADE", index=True
    )
    kind: str = Field(sa_type=String(32))
    data: dict | None = Field(default=None, sa_type=JSONB)
    at: datetime = Field(sa_type=TS)
    received_at: datetime = Field(default_factory=utcnow, sa_type=TS)
