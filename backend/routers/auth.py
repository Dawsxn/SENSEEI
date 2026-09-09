"""Authentication: Google OAuth, the session, and a dev bypass.

The real flow is backend-driven Authorization Code: /login sends the browser to
Google, /callback verifies the result and sets a signed session cookie. The dev
bypass signs in as a seeded user without Google, and is refused in production.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import google_oauth, is_dlsu_email
from ..db import get_session
from ..deps import get_current_user
from ..models import Role, User
from ..schemas import DevLoginIn, UserOut
from ..services import auth_service
from ..settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request):
    """Send the browser to Google, hinting the DLSU domain."""
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    return await google_oauth().google.authorize_redirect(
        request, settings.oauth_redirect_uri, hd="dlsu.edu.ph"
    )


@router.get("/callback")
async def callback(request: Request, db: AsyncSession = Depends(get_session)):
    """Handle Google's redirect: verify, enforce DLSU, sign in, go home."""
    settings = get_settings()
    home = settings.app_base_url.rstrip("/")
    try:
        token = await google_oauth().google.authorize_access_token(request)
    except Exception:
        return RedirectResponse(f"{home}/login?error=oauth")

    info = token.get("userinfo") or {}
    email = info.get("email", "")
    if not info.get("email_verified") or not is_dlsu_email(email):
        # A non-DLSU or unverified account may not sign in.
        return RedirectResponse(f"{home}/login?error=not_dlsu")

    user = await auth_service.upsert_from_google(
        db, sub=info["sub"], email=email, name=info.get("name", "")
    )
    request.session["user_id"] = str(user.id)
    return RedirectResponse(f"{home}/")


@router.post("/logout")
async def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role)


@router.get("/config")
async def config() -> dict:
    """What the sign-in screen needs to know before anyone is signed in."""
    settings = get_settings()
    return {
        "dev_bypass": settings.dev_bypass_enabled,
        "google_configured": bool(settings.google_client_id),
    }


# --------------------------------------------------------------------------- #
# dev bypass — refused in production


def _require_bypass() -> None:
    if not get_settings().dev_bypass_enabled:
        raise HTTPException(status_code=404, detail="not found")


@router.get("/dev/users")
async def dev_users(db: AsyncSession = Depends(get_session)) -> list[dict]:
    """The seeded users to act as, for the dev sign-in screen."""
    _require_bypass()
    users = await db.scalars(select(User).order_by(User.role, User.name))
    return [
        {"id": str(u.id), "name": u.name, "email": u.email, "role": Role(u.role).value}
        for u in users
    ]


@router.post("/dev/login")
async def dev_login(
    body: DevLoginIn, request: Request, db: AsyncSession = Depends(get_session)
) -> dict:
    """Sign in as a seeded user without Google."""
    _require_bypass()
    user = await auth_service.get_by_id(db, body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    request.session["user_id"] = str(user.id)
    return {"ok": True}
