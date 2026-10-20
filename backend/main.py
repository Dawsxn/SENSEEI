"""The FastAPI application: the API routers, a health check, and, once built,
the frontend.

    uvicorn backend.main:app --reload

Locally the frontend runs on Vite and `frontend/dist` does not exist, so only the
API is served. Deployed, the image builds `dist` and this serves it too: one
service on one origin (see backend/frontend.py).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

from .db import dispose, get_session
from .frontend import mount_frontend
from .routers import auth, classes, library, readings, rubric, sessions, trial
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

# Signs the session cookie the auth flow sets. same_site="lax" lets the cookie
# ride the top-level redirect back from Google; https_only is on outside local.
_settings = get_settings()
app.add_middleware(
    SessionMiddleware,
    secret_key=_settings.session_secret,
    same_site="lax",
    https_only=_settings.environment != "local",
)

app.include_router(auth.router)
app.include_router(classes.router)
app.include_router(library.router)
app.include_router(readings.router)
app.include_router(rubric.router)
app.include_router(sessions.router)
app.include_router(trial.router)


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


# Last, after every API route: the frontend's catch-all would shadow anything
# registered after it.
mount_frontend(app, _settings.frontend_dist)
