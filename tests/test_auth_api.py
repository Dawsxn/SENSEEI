"""Auth: the session, the dev bypass, and the callback's rules.

The real Google round-trip can't run in a test, so the callback is exercised by
faking the token Google would return — enough to check the DLSU rule and that a
verified DLSU account gets a session. The dev bypass and the 401 path run for
real against the test database.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.models import Role, User

pytestmark = pytest.mark.usefixtures("fresh_engine")


def make_client() -> AsyncClient:
    from backend.main import app

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    )


@pytest.fixture
async def users(point_app_at_test_db):
    """A seeded student and instructor. Returns their ids."""
    engine = create_async_engine(point_app_at_test_db)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        await s.execute(delete(User))
        await s.commit()
        student = User(role=Role.STUDENT, name="Stu", email="stu@dlsu.edu.ph", google_sub="sub-stu")
        instructor = User(role=Role.INSTRUCTOR, name="Prof", email="prof@dlsu.edu.ph", google_sub="sub-prof")
        s.add_all([student, instructor])
        await s.commit()
        ids = {"student": student.id, "instructor": instructor.id}
    await engine.dispose()
    return ids


# --------------------------------------------------------------------------- #


@pytest.mark.anyio
async def test_me_is_401_without_a_session(users):
    async with make_client() as client:
        r = await client.get("/auth/me")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_dev_login_then_me(users):
    async with make_client() as client:
        r = await client.post("/auth/dev/login", json={"user_id": str(users["instructor"])})
        assert r.status_code == 200
        me = await client.get("/auth/me")  # the cookie from dev/login is reused
    assert me.status_code == 200
    body = me.json()
    assert body["role"] == "instructor"
    assert body["email"] == "prof@dlsu.edu.ph"


@pytest.mark.anyio
async def test_dev_users_lists_the_seeded_accounts(users):
    async with make_client() as client:
        rows = (await client.get("/auth/dev/users")).json()
    emails = {u["email"] for u in rows}
    assert {"stu@dlsu.edu.ph", "prof@dlsu.edu.ph"} <= emails


@pytest.mark.anyio
async def test_logout_clears_the_session(users):
    async with make_client() as client:
        await client.post("/auth/dev/login", json={"user_id": str(users["student"])})
        assert (await client.get("/auth/me")).status_code == 200
        await client.post("/auth/logout")
        assert (await client.get("/auth/me")).status_code == 401


@pytest.mark.anyio
async def test_dev_bypass_is_404_in_production(users, monkeypatch):
    from backend.settings import get_settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    try:
        async with make_client() as client:
            r = await client.get("/auth/dev/users")
        assert r.status_code == 404
    finally:
        get_settings.cache_clear()


@pytest.mark.anyio
async def test_callback_rejects_a_non_dlsu_account(users, monkeypatch):
    from backend import auth as auth_module

    async def fake_token(request):
        return {"userinfo": {"sub": "x", "email": "someone@gmail.com", "email_verified": True, "name": "X"}}

    monkeypatch.setattr(auth_module.google_oauth().google, "authorize_access_token", fake_token)
    async with make_client() as client:
        r = await client.get("/auth/callback")
    assert r.status_code in (302, 307)
    assert "error=not_dlsu" in r.headers["location"]


@pytest.mark.anyio
async def test_callback_signs_in_a_dlsu_account(users, monkeypatch):
    from backend import auth as auth_module

    async def fake_token(request):
        return {"userinfo": {"sub": "new-sub", "email": "new@dlsu.edu.ph", "email_verified": True, "name": "New"}}

    monkeypatch.setattr(auth_module.google_oauth().google, "authorize_access_token", fake_token)
    async with make_client() as client:
        r = await client.get("/auth/callback")
        assert r.status_code in (302, 307)
        assert r.headers["location"].rstrip("/").endswith("localhost:5173")
        me = await client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "new@dlsu.edu.ph"


@pytest.mark.anyio
async def test_instructor_allowlist_sets_the_role(users, monkeypatch):
    from sqlalchemy import select

    from backend.db import sessionmaker
    from backend.services import auth_service

    monkeypatch.setenv("INSTRUCTOR_EMAILS", "boss@dlsu.edu.ph, other@dlsu.edu.ph")
    from backend.settings import get_settings

    get_settings.cache_clear()
    try:
        async with sessionmaker()() as db:
            promoted = await auth_service.upsert_from_google(
                db, sub="s1", email="boss@dlsu.edu.ph", name="Boss"
            )
            plain = await auth_service.upsert_from_google(
                db, sub="s2", email="nobody@dlsu.edu.ph", name="Nobody"
            )
        # role comes back as the stored string; Role is a str-enum so == holds
        assert promoted.role == Role.INSTRUCTOR
        assert plain.role == Role.STUDENT
    finally:
        get_settings.cache_clear()
