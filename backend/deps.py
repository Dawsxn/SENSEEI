"""Request dependencies: who the user is, and which agents to use.

`get_current_user` reads the signed session cookie set at sign-in (real Google
OAuth, or the dev bypass) and loads that user, raising 401 when there is no valid
session. `require_instructor` and `require_student` narrow it to one role, with
403 for the other. `get_agents_dep` is a thin wrapper so a test can override the agent pair
with controllable stubs through FastAPI's dependency_overrides.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.figures import FigureDescriber

from .agent_runtime import Agents, get_agents, get_figure_describer
from .db import get_session
from .models import Role, User
from .services import trial_service
from .settings import get_settings


async def get_current_user(
    request: Request, session: AsyncSession = Depends(get_session)
) -> User:
    """The signed-in user, from the session cookie. 401 if not signed in."""
    raw = request.session.get("user_id")
    if not raw:
        raise HTTPException(status_code=401, detail="not authenticated")
    try:
        user_id = uuid.UUID(raw)
    except ValueError:
        raise HTTPException(status_code=401, detail="not authenticated")
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        # The session points at a user that no longer exists.
        raise HTTPException(status_code=401, detail="not authenticated")
    if user.participant_identifier is not None:
        # A trial participant is signed in only while their ID works: closing
        # the batch or voiding the ID signs them out on their next request, and
        # outside trial mode an ID never works at all.
        participant = await trial_service.participant_for(session, user.id)
        if (
            not get_settings().trial_mode
            or participant is None
            or not await trial_service.is_active(session, participant)
        ):
            request.session.clear()
            raise HTTPException(status_code=401, detail="not authenticated")
    return user


async def require_instructor(user: User = Depends(get_current_user)) -> User:
    """The signed-in user, who must be an instructor. 403 for a student."""
    # The role comes back from the database as its stored string; Role is a
    # str-enum, so compare by equality rather than identity.
    if user.role != Role.INSTRUCTOR:
        raise HTTPException(status_code=403, detail="instructors only")
    return user


async def require_student(user: User = Depends(get_current_user)) -> User:
    """The signed-in user, who must be a student. 403 for an instructor."""
    if user.role != Role.STUDENT:
        raise HTTPException(status_code=403, detail="students only")
    return user


def get_agents_dep() -> Agents:
    """The process-wide agent pair. A seam for tests to override."""
    return get_agents()


def get_figure_describer_dep() -> FigureDescriber:
    """The upload's figure describer. A seam for tests, like the agent pair."""
    return get_figure_describer()
