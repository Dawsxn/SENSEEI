"""The FastAPI application.

Nothing here but the app, its lifespan and a health check. Routes arrive with
the schema and the session API.

    uvicorn backend.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .db import dispose, get_session
from .routers import readings, sessions
from .settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await dispose()


app = FastAPI(
    title="SENSEE-I",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(readings.router)
app.include_router(sessions.router)


@app.get("/health")
async def health(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Is the app up, and can it reach the database?

    The database check is the point. An app that starts but cannot query is the
    failure this endpoint exists to catch.
    """
    try:
        await session.execute(text("SELECT 1"))
        database = "ok"
    except Exception as e:
        database = f"unreachable: {type(e).__name__}"

    return {
        "status": "ok" if database == "ok" else "degraded",
        "environment": settings.environment,
        "database": database,
        "llm_provider": settings.llm_provider,
    }
