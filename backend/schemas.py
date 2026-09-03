"""Request and response shapes for the session API.

Only the non-streaming endpoints use these. The streamed turns emit Server-Sent
Events whose shapes are documented on the service that produces them, because a
stream is a sequence of differently-typed events rather than one model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from .models import SeeiStep, SessionStatus


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
