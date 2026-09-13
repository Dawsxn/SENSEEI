"""Readings, their core components, and which classes they are assigned to."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, LargeBinary, text
from sqlmodel import Field

from .base import TS, Entity, SoftDelete, utcnow


class Reading(Entity, SoftDelete, table=True):
    """An expository text an instructor uploaded.

    A reading has two faces. `content` is the extracted plain text, and it is
    what both agents grade against. `ReadingFile` is the instructor's original
    upload, and it is what the student actually reads on screen.

    Keeping the two faithful to each other is the upload flow's job, not this
    model's: the instructor reviews and corrects the extraction before the
    reading goes live, so `content` is human-approved copy rather than a lossy
    machine guess.
    """

    __tablename__ = "reading"

    uploaded_by: uuid.UUID = Field(
        foreign_key="app_user.id", ondelete="CASCADE", index=True
    )
    title: str
    #: A short one-line topic summary, shown under the title in the reading list.
    #: Nullable: a reading without one simply shows no subtitle. The instructor
    #: will set it on the upload screen; until that exists only the seed does.
    description: str | None = Field(default=None)
    content: str = Field(description="Extracted plain text. This is what the agents see")
    created_at: datetime = Field(default_factory=utcnow, sa_type=TS)


class CoreComponent(Entity, table=True):
    """An essential defining part of the concept the reading covers.

    Immutable after upload. Changing one would invalidate the results and
    statistics of every prior session on that reading, so the API must refuse
    it rather than leaving it to convention.

    No soft delete: these live and die with their reading.
    """

    __tablename__ = "core_component"

    reading_id: uuid.UUID = Field(
        foreign_key="reading.id", ondelete="CASCADE", index=True
    )
    text: str
    position: int = Field(description="Display order")


class ReadingAssignment(Entity, SoftDelete, table=True):
    """Which classes a reading is assigned to.

    Mutable, unlike core components: assignment changes who can see a reading,
    never what it says.
    """

    __tablename__ = "reading_assignment"
    __table_args__ = (
        Index(
            "uq_reading_assignment",
            "reading_id",
            "class_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    reading_id: uuid.UUID = Field(
        foreign_key="reading.id", ondelete="CASCADE", index=True
    )
    class_id: uuid.UUID = Field(foreign_key="class.id", ondelete="CASCADE", index=True)


class ReadingFile(Entity, table=True):
    """The instructor's original upload, kept because the student reads it.

    A separate table rather than a column on `reading`, because the reading list
    loads whole `Reading` rows: a blob on that model would be pulled across the
    wire by every request that only wanted a title. Nothing but the file
    endpoint touches this table.

    No soft delete. Like core components, it lives and dies with its reading.
    """

    __tablename__ = "reading_file"

    #: Unique, not merely indexed: one file per reading is a rule, so it belongs
    #: in the database rather than in the code that happens to write it.
    reading_id: uuid.UUID = Field(
        foreign_key="reading.id", ondelete="CASCADE", unique=True, index=True
    )
    filename: str
    media_type: str = Field(default="application/pdf")
    byte_size: int
    data: bytes = Field(sa_type=LargeBinary)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TS)
