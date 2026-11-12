"""One pass through the four SEE-I steps, and everything it produced.

The chain is session -> attempt -> assessment -> criterion_judgment rather than
fewer, wider tables because the instructor dashboard asks a question at every
level: who finished (session), how many tries they needed (attempt), the pass
rate per step (assessment), and which criteria fail most (criterion_judgment).

None of these carry `deleted_at`. They are the record of what happened, and they
are removed only by a real purge.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from .base import TS, Entity, utcnow
from .enums import SeeiStep, SessionStatus, Verdict


class Session(Entity, table=True):
    """One complete pass through the four steps, for one reading.

    Not resumable. A student who leaves mid-session confirms it will be
    discarded, and the row is discarded with it, so nothing in `in_progress`
    survives them walking away. That discard is a real delete, not a soft one:
    a soft-deleted abandoned session would be junk every analytics query had to
    filter out forever.

    The version columns exist so a session stays interpretable after the rubric
    or a prompt changes. Without them, a rubric revision silently changes the
    meaning of every historical pass rate.
    """

    __tablename__ = "session"

    student_id: uuid.UUID = Field(
        foreign_key="app_user.id", ondelete="CASCADE", index=True
    )
    reading_id: uuid.UUID = Field(
        foreign_key="reading.id", ondelete="CASCADE", index=True
    )

    status: SessionStatus = Field(
        default=SessionStatus.IN_PROGRESS, sa_type=String(16), index=True
    )
    current_step: SeeiStep = Field(default=SeeiStep.STATE, sa_type=String(16))

    started_at: datetime = Field(default_factory=utcnow, sa_type=TS)
    ended_at: datetime | None = Field(default=None, sa_type=TS)

    rubric_version: str
    tutor_prompt_version: str
    assessment_prompt_version: str
    llm_model: str = Field(description="The model that graded this session")


class Attempt(Entity, table=True):
    """One student response to one step. A step can have several.

    Rows rather than a counter, because the dashboard needs the average number
    of tries per step and the transcript view shows the student's whole
    reasoning chain, so every attempt has to survive.

    A failed provider call must never create one of these: a student losing an
    attempt to a network timeout would be invisible in the data and would
    quietly corrupt the per-step attempt statistics.
    """

    __tablename__ = "attempt"
    __table_args__ = (
        # Not partial: attempts are never soft-deleted, and the loop depends on
        # this being impossible to violate.
        Index(
            "uq_attempt_session_step_number",
            "session_id",
            "step",
            "attempt_number",
            unique=True,
        ),
    )

    session_id: uuid.UUID = Field(
        foreign_key="session.id", ondelete="CASCADE", index=True
    )
    step: SeeiStep = Field(sa_type=String(16), index=True)
    attempt_number: int = Field(description="1-based, resets per step")
    response_text: str
    submitted_at: datetime = Field(default_factory=utcnow, sa_type=TS)


class Assessment(Entity, table=True):
    """The Assessment Agent's judgment of one attempt. One to one."""

    __tablename__ = "assessment"

    attempt_id: uuid.UUID = Field(
        foreign_key="attempt.id", ondelete="CASCADE", unique=True, index=True
    )

    #: Derived in code from the criterion judgments: any criterion failing means
    #: FAIL. `model_verdict` is what the model claimed. They are stored
    #: separately on purpose, because a disagreement is a signal worth keeping
    #: rather than collapsing.
    verdict: Verdict = Field(sa_type=String(8), index=True)
    model_verdict: str | None = Field(default=None, sa_type=String(8))

    raw_response: str | None = Field(default=None, description="The model's justification")

    #: Parse warnings (hallucinated or missing criteria) and token counts.
    #: JSONB because both are written once and read whole; no query looks
    #: inside them. criterion_judgment stays relational precisely because the
    #: analytics do query it.
    warnings: list | None = Field(default=None, sa_type=JSONB)
    usage: dict | None = Field(default=None, sa_type=JSONB)

    created_at: datetime = Field(default_factory=utcnow, sa_type=TS)


class CriterionJudgment(Entity, table=True):
    """One row per criterion the agent judged.

    Rows rather than a JSON blob, because the most-failed-criteria statistic is
    a query over this table.
    """

    __tablename__ = "criterion_judgment"
    __table_args__ = (
        Index("ix_criterion_judgment_criterion_passed", "criterion", "passed"),
    )

    assessment_id: uuid.UUID = Field(
        foreign_key="assessment.id", ondelete="CASCADE", index=True
    )
    criterion: str = Field(description="Criterion name, canonical form from the rubric")
    passed: bool
    reason: str | None = None


class TutorMessage(Entity, table=True):
    """The chat transcript, as the student saw it.

    `moves` records which dialogue moves composed the message, so the Tutor
    Agent's behaviour can be checked against the specification later without
    re-inferring intent from prose.
    """

    __tablename__ = "tutor_message"

    session_id: uuid.UUID = Field(
        foreign_key="session.id", ondelete="CASCADE", index=True
    )
    step: SeeiStep = Field(sa_type=String(16))

    #: Null for an opening Prompt, which answers no attempt.
    attempt_id: uuid.UUID | None = Field(
        default=None, foreign_key="attempt.id", ondelete="SET NULL", index=True
    )

    moves: list | None = Field(default=None, sa_type=JSONB)
    content: str
    created_at: datetime = Field(default_factory=utcnow, sa_type=TS)
