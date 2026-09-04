"""Readings, their core components, and which classes they are assigned to."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, text
from sqlmodel import Field

from .base import TS, Entity, SoftDelete, utcnow


class Reading(Entity, SoftDelete, table=True):
    """An expository text an instructor uploaded.

    `content` is the whole story. The original upload is deliberately not
    retained: the instructor reviews and corrects the extracted text before the
    reading goes live, which makes `content` human-approved rather than a lossy
    machine guess, and re-running a better parser over approved copy would be
    pointless. Nothing in the app ever reads the original file.
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
