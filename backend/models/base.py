"""Shared model pieces.

Only the primary key is shared. Timestamps are declared per table under their
own domain names (`enrolled_at`, `started_at`, `submitted_at`), because a single
inherited `created_at` would sit next to those and mean the same thing twice.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Timezone-aware now. Naive datetimes in a TIMESTAMPTZ column are a trap."""
    return datetime.now(timezone.utc)


#: Every timestamp column. Postgres TIMESTAMPTZ, so instants stay unambiguous.
TS = DateTime(timezone=True)


class Entity(SQLModel):
    """A UUID primary key.

    UUIDs rather than serial integers because these ids appear in URLs the
    student sees, and sequential ids let anyone count the rows or walk to
    another student's session by subtracting one.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class SoftDelete(SQLModel):
    """Marks a row deleted without removing it.

    Only on the entities an instructor manages. Deleting a class must not
    vaporise the sessions students completed inside it, which is the same
    reasoning that makes core components immutable after upload.

    Records of what happened (session, attempt, assessment, criterion_judgment,
    tutor_message) deliberately do not get this. Nobody deletes an assessment;
    it is a fact. Those rows go only when a real purge takes them.

    Every query against a soft-deletable table must filter `deleted_at IS NULL`.
    """

    deleted_at: datetime | None = Field(default=None, sa_type=TS, index=True)
