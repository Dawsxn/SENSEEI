"""The tutoring loop, carried out.

This is the imperative shell around the pure Orchestrator: it loads state,
asks the Orchestrator what happens next, and does it — recording attempts,
grading them, and streaming the Tutor's reply. The rules themselves live in
`backend.orchestrator`; nothing here decides pass/fail or advancement.

Everything a student action produces is streamed as Server-Sent Events. Each
streaming function opens its own database session and holds it for the whole
stream, because a request-scoped `Depends` session is closed when the endpoint
returns its response object — which happens before the streamed body runs.

The student hears only the Tutor. The Assessment Agent's verdict and criterion
reasons drive the Orchestrator and are persisted for the instructor dashboard,
but they are never streamed to the student: naming what was missed is the Tutor's
job, done in its own prose. The stream therefore carries no grade, only the
Tutor's messages and the session's position in the loop.

The event types a stream can emit:

    session      the created session (start only)
    message_start  a tutor message begins: its step, kind and moves
    delta        a piece of that message's text
    message_end  the message is complete: its stored id and full content
    state        the session's status, step and attempt progress after the turn
    error        something failed; the stream ends
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from agents.tutor import FIRST_ATTEMPT

from ..agent_runtime import Agents
from ..db import sessionmaker
from ..models import (
    Assessment,
    Attempt,
    CoreComponent,
    CriterionJudgment,
    Reading,
    SeeiStep,
    Session,
    SessionStatus,
    TutorMessage,
    Verdict,
    utcnow,
)
from ..orchestrator import (
    FALLBACK_MESSAGE,
    MAX_ATTEMPTS,
    MOVES,
    Decision,
    attempts_left,
    opening_situation,
    resolve,
)
from ..settings import get_settings


def _sse(event: str, data: dict) -> str:
    """One Server-Sent Event. `default=str` renders UUIDs and datetimes."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _session_payload(sess: Session, reading_title: str) -> dict:
    return {
        "id": str(sess.id),
        "reading_id": str(sess.reading_id),
        "reading_title": reading_title,
        "status": SessionStatus(sess.status).value,
        "current_step": SeeiStep(sess.current_step).value,
        "started_at": sess.started_at.isoformat(),
        "ended_at": sess.ended_at.isoformat() if sess.ended_at else None,
    }


async def _load_reading(db: AsyncSession, reading_id: uuid.UUID) -> Reading | None:
    return await db.scalar(
        select(Reading).where(
            Reading.id == reading_id, Reading.deleted_at.is_(None)
        )
    )


async def _components(db: AsyncSession, reading_id: uuid.UUID) -> list[str]:
    rows = await db.scalars(
        select(CoreComponent.text)
        .where(CoreComponent.reading_id == reading_id)
        .order_by(CoreComponent.position)
    )
    return list(rows)


async def _stream_tutor_message(
    db: AsyncSession,
    agents: Agents,
    session_id: uuid.UUID,
    reading_content: str,
    components: list[str],
    step: SeeiStep,
    situation: str,
    *,
    user_response: str | None = None,
    unmet: list[tuple[str, str]] | None = None,
    give_attempts_left: int | None = None,
    attempt_id: uuid.UUID | None = None,
) -> AsyncIterator[str]:
    """Stream one Tutor message, persist it, and yield its SSE events.

    The synchronous provider stream is iterated in a threadpool so it never
    blocks the event loop. The full text is accumulated as it streams and stored
    once the message is complete.
    """
    moves = MOVES[situation]
    yield _sse("message_start", {"step": step.value, "kind": situation, "moves": moves})

    pieces: list[str] = []
    chunks = agents.tutor.speak_stream(
        reading_content,
        step.value,
        situation,
        core_components=components,
        user_response=user_response,
        unmet=unmet,
        attempts_left=give_attempts_left,
    )
    try:
        async for chunk in iterate_in_threadpool(chunks):
            pieces.append(chunk)
            yield _sse("delta", {"text": chunk})
    except Exception as e:  # a provider failure mid-generation
        yield _sse("error", {"detail": f"tutor failed: {type(e).__name__}"})
        return

    content = "".join(pieces).strip()
    message = TutorMessage(
        session_id=session_id,
        step=step,
        attempt_id=attempt_id,
        moves=moves,
        content=content,
    )
    db.add(message)
    await db.flush()
    yield _sse("message_end", {"id": str(message.id), "content": content})


async def _emit_static_message(
    db: AsyncSession, session_id: uuid.UUID, step: SeeiStep, content: str
) -> AsyncIterator[str]:
    """Store and emit a message that is fixed copy, not Tutor output.

    Only the fallback uses this. It is shown to the student, so it belongs in the
    transcript, but it is labelled `Fallback` rather than carrying dialogue moves
    because the Tutor did not write it.
    """
    yield _sse(
        "message_start", {"step": step.value, "kind": "fallback", "moves": ["Fallback"]}
    )
    yield _sse("delta", {"text": content})
    message = TutorMessage(
        session_id=session_id,
        step=step,
        attempt_id=None,
        moves=["Fallback"],
        content=content,
    )
    db.add(message)
    await db.flush()
    yield _sse("message_end", {"id": str(message.id), "content": content})


# ---------------------------------------------------------------------------
# the two student actions


async def start_session(
    user_id: uuid.UUID, reading_id: uuid.UUID, agents: Agents
) -> AsyncIterator[str]:
    """Create a session for a reading and stream the opening Prompt."""
    settings = get_settings()
    async with sessionmaker()() as db:
        reading = await _load_reading(db, reading_id)
        if reading is None:
            yield _sse("error", {"detail": "reading not found"})
            return

        sess = Session(
            student_id=user_id,
            reading_id=reading_id,
            status=SessionStatus.IN_PROGRESS,
            current_step=SeeiStep.STATE,
            rubric_version=settings.rubric_version,
            tutor_prompt_version=settings.tutor_prompt_version,
            assessment_prompt_version=settings.assessment_prompt_version,
            llm_model=settings.llm_model,
        )
        db.add(sess)
        await db.commit()

        yield _sse("session", _session_payload(sess, reading.title))

        components = await _components(db, reading_id)
        async for ev in _stream_tutor_message(
            db, agents, sess.id, reading.content, components,
            SeeiStep.STATE, opening_situation(),
        ):
            yield ev
        await db.commit()

        yield _sse(
            "state",
            {"status": sess.status.value, "current_step": sess.current_step.value,
             "terminal": False, "attempts_used": 0, "attempts_left": MAX_ATTEMPTS},
        )


async def submit_response(
    user_id: uuid.UUID, session_id: uuid.UUID, text: str, agents: Agents
) -> AsyncIterator[str]:
    """Grade one response, stream the reply, and advance the session."""
    async with sessionmaker()() as db:
        sess = await db.scalar(
            select(Session).where(
                Session.id == session_id, Session.student_id == user_id
            )
        )
        if sess is None:
            yield _sse("error", {"detail": "session not found"})
            return
        # Enum columns are stored as text, so a loaded row hands them back as
        # plain strings; coerce before comparing or indexing on them.
        if SessionStatus(sess.status) is not SessionStatus.IN_PROGRESS:
            yield _sse("error", {"detail": "session has already ended"})
            return

        reading = await _load_reading(db, sess.reading_id)
        if reading is None:
            yield _sse("error", {"detail": "reading not found"})
            return
        components = await _components(db, sess.reading_id)
        step = SeeiStep(sess.current_step)

        prior = await db.scalar(
            select(func.count())
            .select_from(Attempt)
            .where(Attempt.session_id == sess.id, Attempt.step == step)
        )
        attempt_number = (prior or 0) + 1

        # Grade first. A provider failure here must not consume an attempt, so
        # nothing is persisted until the assessment succeeds.
        result = await run_in_threadpool(
            agents.assessor.assess, reading.content, step.value, text
        )
        if not result.parse_ok or result.verdict not in ("PASS", "FAIL"):
            yield _sse(
                "error",
                {"detail": f"assessment failed: {result.error or 'no verdict'}"},
            )
            return

        verdict = Verdict(result.verdict)
        unmet = [
            (name, result.criteria[name].reason if name in result.criteria else "")
            for name in result.fail_criteria
        ]

        # Persist the attempt and its judgment together.
        attempt = Attempt(
            session_id=sess.id,
            step=step,
            attempt_number=attempt_number,
            response_text=text,
        )
        db.add(attempt)
        await db.flush()

        assessment = Assessment(
            attempt_id=attempt.id,
            verdict=verdict,
            model_verdict=result.model_verdict,
            raw_response=result.raw_text,
            warnings=result.warnings or [],
            usage=result.usage,
        )
        db.add(assessment)
        await db.flush()

        for name, judgment in result.criteria.items():
            db.add(
                CriterionJudgment(
                    assessment_id=assessment.id,
                    criterion=name,
                    passed=judgment.passed,
                    reason=judgment.reason or None,
                )
            )
        await db.commit()

        decision: Decision = resolve(step, attempt_number, verdict)

        left = attempts_left(attempt_number)
        async for ev in _stream_tutor_message(
            db, agents, sess.id, reading.content, components, step,
            decision.situation,
            user_response=text,
            unmet=unmet,
            give_attempts_left=left if decision.situation == "retry" else None,
            attempt_id=attempt.id,
        ):
            yield ev

        if decision.fallback:
            async for ev in _emit_static_message(
                db, sess.id, step, FALLBACK_MESSAGE
            ):
                yield ev

        sess.status = decision.new_status
        sess.current_step = decision.new_current_step
        if decision.terminal:
            sess.ended_at = utcnow()
        await db.commit()

        # A pass that advanced owes the opening Prompt of the new step.
        if decision.open_next is not None:
            async for ev in _stream_tutor_message(
                db, agents, sess.id, reading.content, components,
                decision.open_next, FIRST_ATTEMPT,
            ):
                yield ev
            await db.commit()

        # Attempt progress for the step the session now sits on: zero if a pass
        # advanced to a fresh step, otherwise what has been used on this one.
        used = attempt_number if decision.new_current_step == step else 0
        yield _sse(
            "state",
            {
                "status": sess.status.value,
                "current_step": sess.current_step.value,
                "terminal": decision.terminal,
                "attempts_used": used,
                "attempts_left": attempts_left(used),
            },
        )


# ---------------------------------------------------------------------------
# the two reads (plain JSON, no streaming)


async def get_session_state(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> dict | None:
    row = await db.execute(
        select(Session, Reading.title)
        .join(Reading, Reading.id == Session.reading_id)
        .where(Session.id == session_id, Session.student_id == user_id)
    )
    hit = row.first()
    if hit is None:
        return None
    sess, title = hit
    return _session_payload(sess, title)


async def get_transcript(
    db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> list[TutorMessage] | None:
    owns = await db.scalar(
        select(Session.id).where(
            Session.id == session_id, Session.student_id == user_id
        )
    )
    if owns is None:
        return None
    rows = await db.scalars(
        select(TutorMessage)
        .where(TutorMessage.session_id == session_id)
        .order_by(TutorMessage.created_at)
    )
    return list(rows)
