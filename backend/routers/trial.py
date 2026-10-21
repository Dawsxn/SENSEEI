"""Trial endpoints: a participant's own status, clock, Done, chatbot and event
log, and the research team's batches of participant IDs.

Every route here is a 404 unless `TRIAL_MODE` is on, so on any other instance
they do not seem to exist (docs/context/trial.md).

The team's routes live under `/instructor/batches`, not `/participants`, which
is the address of their page: pages and API share one origin.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agents.providers.base import LLMProvider

from ..db import get_session
from ..deps import get_chatbot_dep, require_instructor, require_student
from ..models import User
from ..schemas import (
    BatchIn,
    BatchListItem,
    BatchOut,
    ChatIn,
    ChatMessageOut,
    TrialEventsIn,
    TrialStatusOut,
)
from ..services import chat_service, trial_service
from ..services.trial_service import (
    BatchNotFound,
    InvalidBatch,
    NotDoneable,
    TrialOff,
    UnknownParticipant,
)

router = APIRouter(tags=["trial"])

NOT_FOUND = HTTPException(status_code=404, detail="not found")


# --------------------------------------------------------------------------- #
# a participant


@router.get("/trial/me", response_model=TrialStatusOut)
async def my_status(
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> TrialStatusOut:
    """The participant's mode, reading, time left and session."""
    try:
        return TrialStatusOut(**await trial_service.status(db, user.id))
    except (TrialOff, UnknownParticipant):
        raise NOT_FOUND


@router.post("/trial/clock", response_model=TrialStatusOut)
async def start_clock(
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> TrialStatusOut:
    """Start the participant's time, when their reading opens. Only the first
    call starts it; a reload does not restart it."""
    try:
        return TrialStatusOut(**await trial_service.start_clock(db, user.id))
    except (TrialOff, UnknownParticipant):
        raise NOT_FOUND


@router.post("/trial/done", response_model=TrialStatusOut)
async def finish(
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> TrialStatusOut:
    """Done, for the chatbot and reading-only groups. Pressing it twice, or after
    time is up, changes nothing."""
    try:
        return TrialStatusOut(**await trial_service.finish(db, user.id))
    except (TrialOff, UnknownParticipant):
        raise NOT_FOUND
    except NotDoneable as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/trial/events", status_code=204)
async def record_events(
    body: TrialEventsIn,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """What the participant's browser saw them do, sent in batches."""
    try:
        await trial_service.record(
            db, user.id, [(e.kind, e.at, e.data) for e in body.events]
        )
    except (TrialOff, UnknownParticipant):
        raise NOT_FOUND
    return Response(status_code=204)


@router.get("/trial/chat", response_model=list[ChatMessageOut])
async def chat_history(
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> list[ChatMessageOut]:
    """The chatbot conversation so far, for a reload."""
    try:
        rows = await trial_service.chat_history(db, user.id)
    except (TrialOff, UnknownParticipant):
        raise NOT_FOUND
    return [
        ChatMessageOut(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
        for m in rows
    ]


@router.post("/trial/chat")
async def chat(
    body: ChatIn,
    user: User = Depends(require_student),
    model: LLMProvider = Depends(get_chatbot_dep),
) -> StreamingResponse:
    """Send the chatbot a message and stream its reply."""
    return StreamingResponse(
        chat_service.send(user.id, body.text, model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------------------------------- #
# the research team


@router.get("/instructor/batches", response_model=list[BatchListItem])
async def list_batches(
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> list[BatchListItem]:
    try:
        return [BatchListItem(**b) for b in await trial_service.list_batches(db, user.id)]
    except TrialOff:
        raise NOT_FOUND


@router.post("/instructor/batches", response_model=BatchOut, status_code=201)
async def create_batch(
    body: BatchIn,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> BatchOut:
    """A batch of IDs for one sitting, `count` for each class, drawn shuffled."""
    counts: dict[uuid.UUID, int] = {}
    for row in body.classes:
        counts[row.class_id] = counts.get(row.class_id, 0) + row.count
    try:
        return BatchOut(**await trial_service.create_batch(db, user.id, body.name, counts))
    except TrialOff:
        raise NOT_FOUND
    except InvalidBatch as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/instructor/batches/{batch_id}", response_model=BatchOut)
async def get_batch(
    batch_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> BatchOut:
    try:
        return BatchOut(**await trial_service.get_batch(db, user.id, batch_id))
    except (TrialOff, BatchNotFound):
        raise NOT_FOUND


@router.post("/instructor/batches/{batch_id}/close", response_model=BatchOut)
async def close_batch(
    batch_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> BatchOut:
    """End the sitting. Its IDs stop working and any session still going ends."""
    try:
        return BatchOut(**await trial_service.close_batch(db, user.id, batch_id))
    except (TrialOff, BatchNotFound):
        raise NOT_FOUND


@router.post(
    "/instructor/batches/{batch_id}/participants/{participant_id}/void",
    response_model=BatchOut,
)
async def void_participant(
    batch_id: uuid.UUID,
    participant_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> BatchOut:
    """Stop one ID working."""
    try:
        return BatchOut(
            **await trial_service.void_participant(db, user.id, batch_id, participant_id)
        )
    except (TrialOff, BatchNotFound):
        raise NOT_FOUND
