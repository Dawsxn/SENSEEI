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
