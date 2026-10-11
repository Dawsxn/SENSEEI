"""Request and response shapes for the reading and session APIs.

Only the non-streaming endpoints use these. The streamed turns emit Server-Sent
Events whose shapes are documented on the service that produces them, because a
stream is a sequence of differently-typed events rather than one model.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .models import Role, SeeiStep, SessionStatus


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: Role


class DevLoginIn(BaseModel):
    user_id: uuid.UUID


#: The reading list's per-row status, derived from the student's sessions.
ReadingStatus = Literal["not_started", "complete", "failed"]


class ReadingListItem(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    class_name: str
    status: ReadingStatus


class ReadingDetail(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    class_name: str
    content: str
    core_components: list[str]
    #: Whether the original upload is stored and can be fetched from
    #: `/readings/{id}/file`. False means the reading falls back to `content`.
    has_file: bool


class RubricCriterion(BaseModel):
    name: str
    #: The pass condition, exactly as written in the rubric YAML. Shown to the
    #: student, so it must not be reworded anywhere along the way.
    requirement: str


class RubricStep(BaseModel):
    step: SeeiStep
    criteria: list[RubricCriterion]


class RubricOut(BaseModel):
    version: str
    steps: list[RubricStep]


class StartSessionIn(BaseModel):
    reading_id: uuid.UUID


class SubmitResponseIn(BaseModel):
    text: str


class SessionOut(BaseModel):
    id: uuid.UUID
    reading_id: uuid.UUID
    reading_title: str
    status: SessionStatus
    current_step: SeeiStep
    started_at: datetime
    ended_at: datetime | None


class MessageOut(BaseModel):
    id: uuid.UUID
    step: SeeiStep
    attempt_id: uuid.UUID | None
    moves: list[str] | None
    content: str
    created_at: datetime


# --- review: past sessions on a reading, and one session's replay -------------


class ReadingSessionItem(BaseModel):
    id: uuid.UUID
    index: int  # 1-based order taken; the newest is the highest "Attempt N"
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None
    attempt_count: int


class StepSummary(BaseModel):
    step: SeeiStep
    attempts: int
    passed: bool


class TranscriptEntry(BaseModel):
    role: Literal["tutor", "student", "fallback"]
    step: SeeiStep
    content: str
    attempt_number: int | None
    at: datetime


class SessionTranscript(BaseModel):
    id: uuid.UUID
    reading_id: uuid.UUID
    reading_title: str
    class_name: str
    #: Whose session it is. The student knows; the instructor reading it needs telling.
    student_name: str
    index: int  # which attempt at the reading this session is
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None
    steps: list[StepSummary]
    timeline: list[TranscriptEntry]


# --- classes and enrolment ------------------------------------------------------


class ClassIn(BaseModel):
    """What an instructor types to create or edit a class."""

    name: str = Field(min_length=1, max_length=60)
    section: str = Field(min_length=1, max_length=20)

    @field_validator("name", "section", mode="before")
    @classmethod
    def _trim(cls, value: object) -> object:
        # Whitespace-only must fail the length check, not become a blank class.
        return value.strip() if isinstance(value, str) else value


class ClassListItem(BaseModel):
    id: uuid.UUID
    name: str
    section: str
    #: How students see the class, `STRAMA K31`.
    label: str
    join_code: str
    student_count: int
    reading_count: int


class ClassStudent(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    enrolled_at: datetime


class ClassReading(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None


class ClassDetailOut(BaseModel):
    id: uuid.UUID
    name: str
    section: str
    label: str
    join_code: str
    students: list[ClassStudent]
    readings: list[ClassReading]


class JoinCodeOut(BaseModel):
    join_code: str


class JoinIn(BaseModel):
    join_code: str = Field(min_length=1, max_length=40)


class JoinOut(BaseModel):
    class_id: uuid.UUID
    label: str
    reading_count: int


# --- an instructor's readings ---------------------------------------------------


class ClassRef(BaseModel):
    id: uuid.UUID
    label: str


class LibraryItem(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    #: Labels of the live classes it is assigned to. Empty means no student sees it.
    classes: list[str]
    #: Finished sessions (complete or fallback) by any student.
    session_count: int
    created_at: datetime


class LibraryReading(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    content: str
    core_components: list[str]
    classes: list[ClassRef]
    has_file: bool
    created_at: datetime


class ExtractOut(BaseModel):
    """The PDF as text, for the instructor to check. Nothing has been saved."""

    text: str
    figures_described: int
    #: True when the figures could not be described, so the instructor knows to
    #: write any descriptions themselves.
    figures_failed: bool


class ReadingCreatedOut(BaseModel):
    id: uuid.UUID


class ReadingEditIn(BaseModel):
    """What stays editable after saving: how the reading is labelled."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=200)

    @field_validator("title", "description", mode="before")
    @classmethod
    def _trim(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("description")
    @classmethod
    def _blank_is_none(cls, value: str | None) -> str | None:
        return value or None


class ReadingClassesIn(BaseModel):
    class_ids: list[uuid.UUID]


# --- the class dashboard --------------------------------------------------------


class StepPassRate(BaseModel):
    step: SeeiStep
    passed: int
    total: int
    percent: int


class FailedCriterion(BaseModel):
    criterion: str
    failures: int


class StepAttempts(BaseModel):
    step: SeeiStep
    average: float


class Statistics(BaseModel):
    """The three statistics, over a class or over one reading in it."""

    #: Finished sessions the numbers cover. Zero means the page shows no statistics.
    session_count: int
    pass_rates: list[StepPassRate]
    failed_criteria: list[FailedCriterion]
    average_attempts: list[StepAttempts]


class ClassReadingItem(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    session_count: int


class ClassDashboardOut(BaseModel):
    statistics: Statistics
    readings: list[ClassReadingItem]


#: Where a student got to on one reading: never started, finished, or ran out of
#: attempts and was handed to their instructor.
ReadingProgress = Literal["not_started", "completed", "stopped_early"]


class RosterStudent(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    status: ReadingProgress
    steps_passed: int
    #: The step they ran out of attempts on, when they stopped early.
    stopped_on: SeeiStep | None
    #: Their latest finished session, which the row opens. None if not started.
    session_id: uuid.UUID | None
    last_session_at: datetime | None


class ClassReadingOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    class_id: uuid.UUID
    class_label: str
    statistics: Statistics
    students: list[RosterStudent]
