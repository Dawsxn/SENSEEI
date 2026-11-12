"""Turning a verified Google profile into a user row.

Keyed by the Google subject (`google_sub`), which is stable across email changes.
The role is written from the instructor allowlist on every login, so promoting
someone is a config change that takes effect on their next sign-in.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import is_instructor
from ..models import Role, User


async def upsert_from_google(
    db: AsyncSession, *, sub: str, email: str, name: str
) -> User:
    """Create or update the user for a signed-in Google account."""
    role = Role.INSTRUCTOR if is_instructor(email) else Role.STUDENT
    user = await db.scalar(select(User).where(User.google_sub == sub))
    if user is None:
        user = User(role=role, name=name or email, email=email, google_sub=sub)
    else:
        user.name = name or user.name
        user.email = email
        user.role = role  # allowlist is the source of truth, re-applied each login
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.scalar(select(User).where(User.id == user_id))
