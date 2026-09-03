"""Session endpoints: the tutoring loop over HTTP.

Two actions stream (starting a session, submitting a response), because the
student watches the Tutor's reply appear. Two reads return plain JSON (the
session's state, its transcript), for a page load or a resume.

The streaming endpoints resolve the user and agents as dependencies, then hand
control to the service, which opens its own database session for the life of the
stream. They must not pass the request-scoped session into the stream: it is
closed once this function returns the response object, before the body runs.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent_runtime import Agents
from ..db import get_session
from ..deps import get_agents_dep, get_current_user
from ..models import User
from ..schemas import MessageOut, SessionOut, StartSessionIn, SubmitResponseIn
from ..services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])

#: Headers that keep Server-Sent Events flowing: no client caching, and no proxy
#: buffering (nginx honours X-Accel-Buffering), so chunks arrive as they are sent.
_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.post("")
async def start_session(
    body: StartSessionIn,
    user: User = Depends(get_current_user),
    agents: Agents = Depends(get_agents_dep),
) -> StreamingResponse:
    """Start a session for a reading and stream the opening Prompt."""
    return StreamingResponse(
        session_service.start_session(user.id, body.reading_id, agents),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post("/{session_id}/responses")
async def submit_response(
    session_id: uuid.UUID,
    body: SubmitResponseIn,
    user: User = Depends(get_current_user),
    agents: Agents = Depends(get_agents_dep),
) -> StreamingResponse:
    """Submit one attempt; stream the assessment result and the Tutor's reply."""
    return StreamingResponse(
        session_service.submit_response(user.id, session_id, body.text, agents),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.get("/{session_id}", response_model=SessionOut)
async def get_session_state(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> SessionOut:
    """The session's current status and step, for a page load or resume."""
    state = await session_service.get_session_state(db, user.id, session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="session not found")
    return SessionOut(**state)


@router.get("/{session_id}/messages", response_model=list[MessageOut])
async def get_transcript(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[MessageOut]:
    """The full transcript of the session, as the student saw it."""
    messages = await session_service.get_transcript(db, user.id, session_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="session not found")
    return [
        MessageOut(
            id=m.id,
            step=m.step,
            attempt_id=m.attempt_id,
            moves=m.moves,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]
