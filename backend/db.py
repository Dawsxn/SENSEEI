"""Async database engine and the per-request session.

Async because a tutoring turn spends most of its time waiting: several seconds on
the Assessment Agent, several more on the Tutor Agent. A request that yields
while it waits does not hold a worker, which is also what makes streaming the
Tutor's reply possible later.

No models here yet. They arrive with the schema.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .settings import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        s = get_settings()
        _engine = create_async_engine(
            s.database_url,
            echo=s.db_echo,
            pool_pre_ping=True,   # a pooled connection can be dead after a restart
            # Up to 25 at once, not the default 15: a trial sitting of 45 can
            # submit answers together, each holding one while it is graded. Kept
            # well under the database's 100, whose smallest plan has 256 MB.
            pool_size=10,
            max_overflow=15,
        )
    return _engine


def sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            engine(),
            expire_on_commit=False,   # keep objects usable after the request commits
            autoflush=False,
        )
    return _sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency. One session per request, rolled back on error."""
    async with sessionmaker()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose() -> None:
    """Close the pool on shutdown, so nothing is left hanging."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
