import pytest

from backend.db import dispose


@pytest.fixture
def anyio_backend():
    """anyio runs async tests; pin it to asyncio rather than also trying trio."""
    return "asyncio"


@pytest.fixture(autouse=True)
async def fresh_engine():
    """Drop the cached engine after every test.

    backend/db.py caches the engine in a module global, which is right in
    production: uvicorn runs one event loop for the whole process, so one pool
    is correct. Under test, anyio gives each test its own loop, so the second
    test would inherit connections bound to the first test's closed loop and
    fail with an AttributeError from deep inside asyncpg.
    """
    yield
    await dispose()
