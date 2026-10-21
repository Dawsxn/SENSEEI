"""The trial's data, for analysis: one zip of spreadsheet files.

Everything is keyed by participant ID. No file holds a name or an email, because
the trial instance never has any (docs/context/trial.md). Each file opens
directly in Excel, SPSS, R or Python. Times are UTC, in ISO 8601.

Only trial participants are exported, from every batch: the trial instance
holds nothing else, and the study's data is all of theirs, whoever on the team
made the batch.
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Assessment,
    Attempt,
    ChatMessage,
    Class,
    CriterionJudgment,
    Participant,
    ParticipantBatch,
    Reading,
    Session,
    TrialEvent,
    TutorMessage,
    class_label,
)
from .trial_service import deadline, require_trial

README = """SENSEE-I trial export

Every file is keyed by participant_id, the ID on the participant's slip.
Times are UTC (ISO 8601).

participants.csv    one row per ID: batch, class, group, and when they signed in,
                    opened the reading, pressed Done, and when their time ran out
sessions.csv        the SEE-I group's sessions: how each ended and on which step
attempts.csv        every SEE-I answer, with its verdict
criteria.csv        every criterion judged on every answer, with the reason
tutor_messages.csv  everything the tutor said, in order
chat_messages.csv   the chatbot group's conversations, both sides
events.csv          what each participant did: panels, pages, pastes (length
                    only), replies shown, first keystrokes, leaving the tab
"""


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _csv(header: list[str], rows) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


async def export(db: AsyncSession) -> bytes:
    """The zip, as bytes. Small enough to build in memory: a trial is tens of
    participants, not thousands."""
    require_trial()

    people = (
        await db.execute(
            select(Participant, ParticipantBatch.name, class_label(), Class.mode)
            .join(ParticipantBatch, ParticipantBatch.id == Participant.batch_id)
            .join(Class, Class.id == Participant.class_id)
            .order_by(ParticipantBatch.created_at, Participant.position)
        )
    ).all()
    by_user = {p.user_id: p.code for p, _, _, _ in people}
    by_participant = {p.id: p.code for p, _, _, _ in people}
    users = list(by_user)

    files: dict[str, str] = {"README.txt": README}
    files["participants.csv"] = _csv(
        ["participant_id", "batch", "class", "group", "signed_in_at", "reading_opened_at",
         "done_at", "time_ran_out_at", "voided_at"],
        [
            [p.code, batch, label, mode, _iso(p.signed_in_at), _iso(p.clock_started_at),
             _iso(p.done_at), _iso(deadline(p)), _iso(p.voided_at)]
            for p, batch, label, mode in people
        ],
    )

    sessions = (
        await db.execute(
            select(Session, Reading.title)
            .join(Reading, Reading.id == Session.reading_id)
            .where(Session.student_id.in_(users))
            .order_by(Session.started_at)
        )
    ).all()
    files["sessions.csv"] = _csv(
        ["participant_id", "session_id", "reading", "status", "last_step", "started_at",
         "ended_at", "rubric_version", "tutor_prompt_version", "assessment_prompt_version",
         "model"],
        [
            [by_user[s.student_id], s.id, title, s.status, s.current_step, _iso(s.started_at),
             _iso(s.ended_at), s.rubric_version, s.tutor_prompt_version,
             s.assessment_prompt_version, s.llm_model]
            for s, title in sessions
        ],
    )
    owner = {s.id: by_user[s.student_id] for s, _ in sessions}

    attempts = (
        await db.execute(
            select(Attempt, Assessment)
            .outerjoin(Assessment, Assessment.attempt_id == Attempt.id)
            .where(Attempt.session_id.in_(list(owner)))
            .order_by(Attempt.submitted_at)
        )
    ).all()
    files["attempts.csv"] = _csv(
        ["participant_id", "session_id", "step", "attempt_number", "submitted_at", "verdict",
         "model_verdict", "response_text"],
        [
            [owner[a.session_id], a.session_id, a.step, a.attempt_number, _iso(a.submitted_at),
             x.verdict if x else "", (x.model_verdict or "") if x else "", a.response_text]
            for a, x in attempts
        ],
    )

    judged = (
        await db.execute(
            select(CriterionJudgment, Attempt)
            .join(Assessment, Assessment.id == CriterionJudgment.assessment_id)
            .join(Attempt, Attempt.id == Assessment.attempt_id)
            .where(Attempt.session_id.in_(list(owner)))
            .order_by(Attempt.submitted_at, CriterionJudgment.criterion)
        )
    ).all()
    files["criteria.csv"] = _csv(
        ["participant_id", "session_id", "step", "attempt_number", "criterion", "passed",
         "reason"],
        [
            [owner[a.session_id], a.session_id, a.step, a.attempt_number, j.criterion,
             j.passed, j.reason or ""]
            for j, a in judged
        ],
    )

    tutor = await db.scalars(
        select(TutorMessage)
        .where(TutorMessage.session_id.in_(list(owner)))
        .order_by(TutorMessage.created_at)
    )
    files["tutor_messages.csv"] = _csv(
        ["participant_id", "session_id", "step", "moves", "created_at", "content"],
        [
            [owner[m.session_id], m.session_id, m.step, " + ".join(m.moves or []),
             _iso(m.created_at), m.content]
            for m in tutor
        ],
    )

    chat = await db.scalars(
        select(ChatMessage)
        .where(ChatMessage.participant_id.in_(list(by_participant)))
        .order_by(ChatMessage.created_at)
    )
    files["chat_messages.csv"] = _csv(
        ["participant_id", "role", "created_at", "content"],
        [[by_participant[m.participant_id], m.role, _iso(m.created_at), m.content] for m in chat],
    )

    events = await db.scalars(
        select(TrialEvent)
        .where(TrialEvent.participant_id.in_(list(by_participant)))
        .order_by(TrialEvent.participant_id, TrialEvent.at)
    )
    files["events.csv"] = _csv(
        ["participant_id", "kind", "data", "at", "received_at"],
        [
            [by_participant[e.participant_id], e.kind,
             json.dumps(e.data, sort_keys=True) if e.data else "", _iso(e.at),
             _iso(e.received_at)]
            for e in events
        ],
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, text in files.items():
            # A byte-order mark, so Excel reads the text as UTF-8.
            zf.writestr(name, ("﻿" if name.endswith(".csv") else "") + text)
    return buffer.getvalue()
