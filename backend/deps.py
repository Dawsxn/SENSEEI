"""Request dependencies: who the user is, and which agents to use.

`get_current_user` reads the signed session cookie set at sign-in (real Google
OAuth, or the dev bypass) and loads that user, raising 401 when there is no valid
session. `get_agents_dep` is a thin wrapper so a test can override the agent pair
with controllable stubs through FastAPI's dependency_overrides.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .agent_runtime import Agents, get_agents
from .db import get_session
from .models import User


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
    return user


def get_agents_dep() -> Agents:
    """The process-wide agent pair. A seam for tests to override."""
    return get_agents()
