"""Request dependencies: who the user is, and which agents to use.

Both are deliberately swappable. `get_current_user` is a stub that returns a
seeded student, so the whole tutoring loop can be built and tested before real
Google sign-in exists; the `feat/auth` branch replaces this one function with
OAuth and nothing else in the API has to change. `get_agents_dep` is a thin
wrapper so a test can override the agent pair with controllable stubs through
FastAPI's dependency_overrides.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .agent_runtime import Agents, get_agents
from .db import get_session
from .models import Role, User

#: The seeded student the stub signs in as. Matches scripts/seed.py.
STUB_GOOGLE_SUB = "seed-student-1"


async def get_current_user(session: AsyncSession = Depends(get_session)) -> User:
    """The signed-in student. A stub until `feat/auth` lands real OAuth.

    Returns the seeded student, so local development has a real user row to hang
    sessions off. If the database has not been seeded, this fails loudly rather
    than inventing a user, because a session with no owner would violate the
    foreign key anyway.
    """
    user = await session.scalar(
        select(User).where(User.google_sub == STUB_GOOGLE_SUB)
    )
    if user is None:
        # Fall back to any student, so a differently-seeded database still works.
        user = await session.scalar(
            select(User).where(User.role == Role.STUDENT).order_by(User.created_at)
        )
    if user is None:
        raise HTTPException(
            status_code=503,
            detail="No student in the database. Run: python scripts/seed.py",
        )
    return user


def get_agents_dep() -> Agents:
    """The process-wide agent pair. A seam for tests to override."""
    return get_agents()
