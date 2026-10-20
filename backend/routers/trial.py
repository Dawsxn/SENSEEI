"""Trial endpoints: a participant's own status and clock, and the research
team's batches of participant IDs.

Every route here is a 404 unless `TRIAL_MODE` is on, so on any other instance
they do not seem to exist (docs/context/trial.md).

The team's routes live under `/instructor/batches`, not `/participants`, which
is the address of their page: pages and API share one origin.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import require_instructor, require_student
from ..models import User
from ..schemas import BatchIn, BatchListItem, BatchOut, TrialStatusOut
from ..services import trial_service
from ..services.trial_service import (
    BatchNotFound,
    InvalidBatch,
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
