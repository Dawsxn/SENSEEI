"""Authentication: Google OAuth, the session, and acting as a seeded user.

The real flow is backend-driven Authorization Code: /login sends the browser to
Google, /callback verifies the result and sets a signed session cookie.

Acting as a seeded user, without Google, is allowed in two cases and refused in
production in both:

- **The dev bypass**, an open picker on the sign-in screen. For local work only:
  on a public URL it would let anyone in as anyone.
- **QA switching**, for a deployed development environment. Someone whose email
  is in `QA_EMAILS` signs in with Google as themselves, and may then switch to
  any seeded user from the account menu. The session remembers who they really
  are, so they can keep switching; logging out forgets it. Anyone else still has
  to get past Google, and gets no switch.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import google_oauth, is_dlsu_email, is_instructor
from ..db import get_session
from ..deps import get_current_user
from ..models import Role, User
from ..schemas import DevLoginIn, ParticipantSignInIn, UserOut
from ..services import auth_service, trial_service
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
    if settings.trial_mode and not is_instructor(email):
        # On the trial instance Google is the research team's way in, and only
        # theirs. Participants sign in with an ID.
        return RedirectResponse(f"{home}/login?error=not_team")

    user = await auth_service.upsert_from_google(
        db, sub=info["sub"], email=email, name=info.get("name", "")
    )
    request.session["user_id"] = str(user.id)
    if email.strip().lower() in settings.qa_allowlist:
        request.session["qa_email"] = email.strip().lower()
    return RedirectResponse(f"{home}/")


@router.post("/logout")
async def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(request: Request, user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        can_switch=may_act_as(request),
        participant=user.participant_identifier is not None,
    )


@router.get("/config")
async def config() -> dict:
    """What the sign-in screen needs to know before anyone is signed in."""
    settings = get_settings()
    return {
        "dev_bypass": settings.dev_bypass_enabled,
        "google_configured": bool(settings.google_client_id),
        "trial_mode": settings.trial_mode,
    }


@router.post("/participant")
async def participant_sign_in(
    body: ParticipantSignInIn, request: Request, db: AsyncSession = Depends(get_session)
) -> dict:
    """Trial mode: sign in with a participant ID, and nothing else.

    The ID is the whole credential. It works because it is random, only issued
    IDs exist, and a batch is open only for its sitting (docs/context/trial.md).
    """
    try:
        user = await trial_service.sign_in(db, body.code)
    except trial_service.TrialOff:
        raise HTTPException(status_code=404, detail="not found")
    except trial_service.UnknownParticipant:
        raise HTTPException(status_code=404, detail="unknown participant ID")
    except trial_service.InactiveParticipant:
        raise HTTPException(status_code=403, detail="participant ID no longer active")
    request.session.clear()
    request.session["user_id"] = str(user.id)
    return {"ok": True}


# --------------------------------------------------------------------------- #
# acting as a seeded user — refused in production


def may_act_as(request: Request) -> bool:
    """The dev bypass, or a QA tester who signed in with Google as themselves.

    The tester list is re-read on every request, so taking someone off it ends
    their switching at once rather than when their cookie expires.
    """
    settings = get_settings()
    if settings.dev_bypass_enabled:
        return True
    return request.session.get("qa_email") in settings.qa_allowlist


def _require_act_as(request: Request) -> None:
    # 404 rather than 403: in production these routes should not seem to exist.
    if not may_act_as(request):
        raise HTTPException(status_code=404, detail="not found")


@router.get("/dev/users")
async def dev_users(request: Request, db: AsyncSession = Depends(get_session)) -> list[dict]:
    """The users to act as: the dev sign-in screen's list, and the switch menu's."""
    _require_act_as(request)
    # Trial participants sign in with their ID, the way they will on the day,
    # and a sitting's worth of them would bury everyone else in the list.
    users = await db.scalars(
        select(User)
        .where(User.participant_identifier.is_(None))
        .order_by(User.role, User.name)
    )
    return [
        {"id": str(u.id), "name": u.name, "email": u.email, "role": Role(u.role).value}
        for u in users
    ]


@router.post("/dev/login")
async def dev_login(
    body: DevLoginIn, request: Request, db: AsyncSession = Depends(get_session)
) -> dict:
    """Act as a seeded user without Google. A QA tester keeps their `qa_email`,
    so they can switch again."""
    _require_act_as(request)
    user = await auth_service.get_by_id(db, body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    request.session["user_id"] = str(user.id)
    return {"ok": True}
