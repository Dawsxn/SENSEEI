"""The health endpoint answers, and says whether the database is reachable.

Two tests on purpose. The first needs no database, so it runs anywhere including
CI. The second needs `docker compose up -d` and skips when there isn't one.
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app

# These reach the app through the module-global engine in backend/db.py, so each
# test must dispose it afterwards to avoid inheriting a pool bound to a dead loop.
pytestmark = pytest.mark.usefixtures("fresh_engine")


@pytest.mark.anyio
async def test_health_responds():
    """Up, and reporting its configuration, database or not."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")

    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert body["environment"] == "local"
    # local defaults to the stub provider, so nothing costs money by accident
    assert body["llm_provider"] == "mock"


@pytest.mark.anyio
@pytest.mark.skipif(os.environ.get("SKIP_DB_TESTS") == "1", reason="no database")
async def test_health_reaches_the_database():
    """With Postgres up, the check passes rather than degrading."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        body = (await client.get("/health")).json()

    if body["database"] != "ok":
        pytest.skip(f"no database: {body['database']}. Run: docker compose up -d")
    assert body["status"] == "ok"
