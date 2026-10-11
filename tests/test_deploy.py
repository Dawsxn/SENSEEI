"""What only matters once deployed: serving the built frontend, and reading the
database URL the way a host hands it out.

The frontend is served from a fake `dist` in a temporary folder, on a fresh app,
so these run without building anything and without a database.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.frontend import mount_frontend
from backend.settings import Settings


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>app</title>")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    (tmp_path / "assets" / "index-abc.js").write_text("console.log(1)")
    (tmp_path / "assets" / "pdf.worker.min-abc.mjs").write_text("export {}")
    (tmp_path.parent / "secret.txt").write_text("outside dist")
    return tmp_path


@pytest.fixture
def client(dist):
    app = FastAPI()

    @app.get("/instructor/classes")
    async def api() -> list:
        return []

    assert mount_frontend(app, dist)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_a_page_path_loads_the_app_so_a_refresh_works(client):
    async with client:
        for path in ("/", "/classes/abc", "/library/new", "/review/xyz"):
            r = await client.get(path)
            assert r.status_code == 200, path
            assert "<title>app</title>" in r.text
            assert r.headers["cache-control"] == "no-cache"


@pytest.mark.anyio
async def test_the_api_still_answers_before_the_app_does(client):
    async with client:
        assert (await client.get("/instructor/classes")).json() == []


@pytest.mark.anyio
async def test_an_unknown_api_path_is_a_json_404_not_the_app(client):
    async with client:
        for path in ("/instructor/nope", "/readings/x/y/z", "/auth/whatever", "/sessions"):
            r = await client.get(path)
            assert r.status_code == 404, path
            assert r.headers["content-type"].startswith("application/json")


@pytest.mark.anyio
async def test_built_files_are_served_as_themselves(client):
    async with client:
        js = await client.get("/assets/index-abc.js")
        worker = await client.get("/assets/pdf.worker.min-abc.mjs")
        icon = await client.get("/favicon.svg")
    assert js.text == "console.log(1)"
    # The PDF viewer's worker refuses to start if this is not JavaScript.
    assert "javascript" in worker.headers["content-type"]
    assert icon.text == "<svg/>"


@pytest.mark.anyio
async def test_nothing_outside_dist_can_be_read(client):
    async with client:
        r = await client.get("/..%2Fsecret.txt")
    assert "outside dist" not in r.text


def test_nothing_is_mounted_when_the_frontend_was_never_built(tmp_path):
    # Local development: Vite serves the frontend, and the API stays API-only.
    assert mount_frontend(FastAPI(), tmp_path) is False


# --------------------------------------------------------------------------- #
# settings


@pytest.mark.parametrize(
    "given, expected",
    [
        ("postgres://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        ("postgresql://u:p@h:5432/db", "postgresql+asyncpg://u:p@h:5432/db"),
        ("postgresql://u:p@h/db?sslmode=require", "postgresql+asyncpg://u:p@h/db?ssl=require"),
        ("postgresql+asyncpg://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
    ],
)
def test_a_hosts_database_url_is_read_with_the_async_driver(given, expected):
    assert Settings(database_url=given).database_url == expected


def test_qa_switching_does_not_exist_in_production():
    assert Settings(qa_emails="me@dlsu.edu.ph", environment="development").qa_allowlist == {
        "me@dlsu.edu.ph"
    }
    assert Settings(qa_emails="me@dlsu.edu.ph", environment="production").qa_allowlist == set()


@pytest.mark.parametrize("given, expected", [("", "mock"), ("  ", "mock"), ("Gemini", "gemini")])
def test_an_empty_provider_setting_means_the_free_mock(given, expected):
    # A dashboard leaves an unset variable empty, and empty must not cost money.
    assert Settings(llm_provider=given).llm_provider == expected
