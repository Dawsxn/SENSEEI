import asyncio
from urllib.parse import urlsplit, urlunsplit

import pytest

#: A throwaway database, separate from whatever `senseei` holds for development,
#: so the DB-backed tests never touch seeded dev data.
TEST_DB = "senseei_test"


def swap_database(url: str, name: str) -> str:
    """Return `url` pointing at a different database on the same server."""
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{name}"))


async def _create_test_database(admin_url: str) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB}
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """A created and migrated `senseei_test`, or skip the DB-backed tests.

    Synchronous on purpose: Alembic's command API runs its own event loop through
    migrations/env.py, so keeping this out of anyio avoids fighting over fixture
    scope. Applying the migration here is what the schema and session-API tests
    build on.
    """
    from backend.settings import get_settings

    settings = get_settings()
    admin_url = swap_database(settings.database_url, "senseei")
    test_url = swap_database(settings.database_url, TEST_DB)

    try:
        asyncio.run(_create_test_database(admin_url))
    except Exception as e:
        pytest.skip(
            f"no database: {type(e).__name__}. Run: docker compose up -d --wait"
        )

    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", test_url)
    command.upgrade(cfg, "head")
    return test_url


@pytest.fixture
def anyio_backend():
    """anyio runs async tests; pin it to asyncio rather than also trying trio."""
    return "asyncio"


@pytest.fixture
def point_app_at_test_db(test_database_url):
    """Make the app's global engine and settings use the test database.

    A service opens its own session through the module-global engine, so the app
    has to be pointed at `senseei_test` for the duration of the test, then
    restored so the health tests still see the dev database.
    """
    import os

    from backend.settings import get_settings

    original = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_database_url
    get_settings.cache_clear()
    yield test_database_url
    if original is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = original
    get_settings.cache_clear()


@pytest.fixture
async def fresh_engine():
    """Drop the cached engine after a test that used the module-global one.

    backend/db.py caches the engine in a module global, which is right in
    production: uvicorn runs one event loop for the whole process, so one pool
    is correct. Under test, anyio gives each test its own loop, so a second test
    would inherit connections bound to the first test's closed loop and fail
    with an AttributeError from deep inside asyncpg.

    It is not autouse: only tests that reach the app through the global engine
    (the health and session-API tests) need it, and an async autouse fixture
    cannot attach to the synchronous Orchestrator tests. Those test files opt in
    with `pytestmark = pytest.mark.usefixtures("fresh_engine")`.
    """
    from backend.db import dispose

    yield
    await dispose()
