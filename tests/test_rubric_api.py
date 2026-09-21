"""The rubric endpoint.

The student is told which criteria a response missed and can look up what each
one asks for, so what this serves has to be the rubric's own words. The test
that matters compares the response against the YAML on disk rather than against
a copy written here, which would only prove that two hand-typed strings match.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

# point_app_at_test_db: skip cleanly without a database, like every other API
# test, and never read the development database through the signed-in stub.
pytestmark = pytest.mark.usefixtures(
    "point_app_at_test_db", "fresh_engine", "auth_seed_student"
)

ROOT = Path(__file__).resolve().parent.parent


def make_client() -> AsyncClient:
    from backend.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def on_disk() -> dict:
    from backend.settings import get_settings

    version = get_settings().rubric_version
    path = ROOT / "agents" / "rubrics" / f"rubric_{version}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.anyio
async def test_serves_every_step_in_rubric_order():
    async with make_client() as client:
        body = (await client.get("/rubric")).json()

    assert [s["step"] for s in body["steps"]] == list(on_disk())


@pytest.mark.anyio
async def test_requirements_are_the_rubrics_own_words():
    """Verbatim. A paraphrase would show the student one standard while the
    Assessment Agent grades against another."""
    async with make_client() as client:
        body = (await client.get("/rubric")).json()

    disk = on_disk()
    for step in body["steps"]:
        expected = disk[step["step"]]
        assert [c["name"] for c in step["criteria"]] == list(expected)
        for criterion in step["criteria"]:
            assert criterion["requirement"] == expected[criterion["name"]]["pass"]


@pytest.mark.anyio
async def test_reports_the_pinned_version():
    from backend.settings import get_settings

    async with make_client() as client:
        body = (await client.get("/rubric")).json()

    assert body["version"] == get_settings().rubric_version
