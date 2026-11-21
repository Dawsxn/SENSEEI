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
from ..deps import get_chatbot_dep, require_grader, require_instructor, require_student
from ..models import User, utcnow
from ..schemas import (
    BatchIn,
    BatchListItem,
    BatchOut,
    ChatIn,
    ChatMessageOut,
    GradingDetailOut,
    GradingListItem,
    SavedAnswer,
    ScoreIn,
    TestAnswerIn,
    TestViewOut,
    TestWhich,
    TrialEventsIn,
    TrialStatusOut,
)
from ..services import chat_service, export_service, test_service, trial_service
from ..services.detach import detached
from ..services.trial_service import (
    BatchNotFound,
    InvalidBatch,
    BatchOpen,
    NotDoneable,
    PretestFirst,
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
    except PretestFirst:
        raise HTTPException(status_code=409, detail="the pre-test comes first")


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


# --------------------------------------------------------------------------- #
# a participant's pre-test and post-test


def _test_errors(e: Exception) -> HTTPException:
    if isinstance(e, (TrialOff, UnknownParticipant, test_service.UnknownItem)):
        return NOT_FOUND
    if isinstance(e, test_service.NotOpen):
        return HTTPException(status_code=409, detail=str(e))
    return HTTPException(status_code=422, detail=str(e))


TEST_ERRORS = (
    TrialOff,
    UnknownParticipant,
    test_service.UnknownItem,
    test_service.NotOpen,
    test_service.BadAnswer,
)


@router.get("/trial/tests/{which}", response_model=TestViewOut)
async def view_test(
    which: TestWhich,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> TestViewOut:
    """The test as its taker sees it, with their saved answers. No answer key."""
    try:
        return TestViewOut(**await test_service.view(db, user.id, which))
    except TEST_ERRORS as e:
        raise _test_errors(e)


@router.post("/trial/tests/{which}/start", response_model=TestViewOut)
async def start_test(
    which: TestWhich,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> TestViewOut:
    """Start the test's clock. Only the first call starts it."""
    try:
        return TestViewOut(**await test_service.start(db, user.id, which))
    except TEST_ERRORS as e:
        raise _test_errors(e)


@router.put("/trial/tests/{which}/answers/{item}", response_model=SavedAnswer)
async def save_answer(
    which: TestWhich,
    item: str,
    body: TestAnswerIn,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> SavedAnswer:
    """Save one answer as it is typed."""
    try:
        saved = await test_service.save(
            db, user.id, which, item,
            choice=body.choice,
            text=body.text,
            groups=None if body.groups is None else [g.model_dump() for g in body.groups],
            sure=body.sure,
        )
    except TEST_ERRORS as e:
        raise _test_errors(e)
    return SavedAnswer(**saved)


@router.post("/trial/tests/{which}/submit", response_model=TrialStatusOut)
async def submit_test(
    which: TestWhich,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> TrialStatusOut:
    """Submit the test. It cannot be changed afterwards."""
    try:
        await test_service.submit(db, user.id, which)
        return TrialStatusOut(**await trial_service.status(db, user.id))
    except TEST_ERRORS as e:
        raise _test_errors(e)


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
        detached(chat_service.send(user.id, body.text, model)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------------------------------- #
# the research team


@router.get("/instructor/export")
async def export(
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """Everything the trial recorded, as a zip of spreadsheet files keyed by
    participant ID."""
    try:
        data = await export_service.export(db)
    except TrialOff:
        raise NOT_FOUND
    day = utcnow().date().isoformat()
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="senseei-trial-{day}.zip"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/instructor/grading", response_model=list[GradingListItem])
async def grading_list(
    user: User = Depends(require_grader),
    db: AsyncSession = Depends(get_session),
) -> list[GradingListItem]:
    """Everyone with a test to grade, by ID only."""
    try:
        return [GradingListItem(**row) for row in await test_service.grading_list(db)]
    except TrialOff:
        raise NOT_FOUND


@router.get("/instructor/grading/{code}", response_model=GradingDetailOut)
async def grading_detail(
    code: str,
    user: User = Depends(require_grader),
    db: AsyncSession = Depends(get_session),
) -> GradingDetailOut:
    """One participant's answers, scores and rubrics. Never their group."""
    try:
        return GradingDetailOut(**await test_service.grading_detail(db, code))
    except (TrialOff, test_service.NotGradable):
        raise NOT_FOUND


@router.put("/instructor/grading/{code}/{which}/{item}", response_model=GradingDetailOut)
async def set_score(
    code: str,
    which: TestWhich,
    item: str,
    body: ScoreIn,
    user: User = Depends(require_grader),
    db: AsyncSession = Depends(get_session),
) -> GradingDetailOut:
    """Score one written answer. A score can be changed any time."""
    try:
        return GradingDetailOut(
            **await test_service.set_score(db, code, which, item, body.score)
        )
    except (TrialOff, test_service.NotGradable):
        raise NOT_FOUND
    except test_service.BadScore as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/instructor/participants/{code}", status_code=204)
async def withdraw(
    code: str,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """A participant withdraws: everything recorded for their ID is deleted."""
    try:
        await trial_service.withdraw(db, code)
    except (TrialOff, UnknownParticipant):
        raise NOT_FOUND
    return Response(status_code=204)


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


@router.delete("/instructor/batches/{batch_id}", status_code=204)
async def delete_batch(
    batch_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """Delete a closed batch and everything recorded for every ID in it."""
    try:
        await trial_service.delete_batch(db, user.id, batch_id)
    except (TrialOff, BatchNotFound):
        raise NOT_FOUND
    except BatchOpen:
        raise HTTPException(status_code=409, detail="close the batch first")
    return Response(status_code=204)


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
