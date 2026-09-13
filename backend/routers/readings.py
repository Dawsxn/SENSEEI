"""Reading endpoints: what a student can see, one reading's detail, and its file.

All are scoped to the signed-in student. Visibility is enforced in the service,
and every endpoint here returns 404 for a reading the student cannot see, so an
unassigned id looks the same as a missing one.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..models import User
from ..schemas import ReadingDetail, ReadingListItem, ReadingSessionItem
from ..services import reading_service, review_service

router = APIRouter(prefix="/readings", tags=["readings"])


@router.get("", response_model=list[ReadingListItem])
async def list_readings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[ReadingListItem]:
    """The readings assigned to the classes this student is enrolled in."""
    rows = await reading_service.list_readings(db, user.id)
    return [ReadingListItem(**row) for row in rows]


@router.get("/{reading_id}", response_model=ReadingDetail)
async def get_reading(
    reading_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ReadingDetail:
    """One reading's text, class and core components, for the tutoring screen."""
    detail = await reading_service.get_reading_detail(db, user.id, reading_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="reading not found")
    return ReadingDetail(**detail)


@router.get("/{reading_id}/file")
async def get_reading_file(
    reading_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """The reading's original upload, which is what the student reads on screen.

    `private` caching because the response is scoped to the signed-in student and
    must never be held by a shared cache. It is cacheable at all because a
    reading's file does not change once uploaded, and the same file is fetched
    again each time the student re-enters the reading.
    """
    file = await reading_service.get_reading_file(db, user.id, reading_id)
    if file is None:
        raise HTTPException(status_code=404, detail="reading file not found")
    return Response(
        content=file.data,
        media_type=file.media_type,
        headers={
            "Content-Disposition": f'inline; filename="{file.filename}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get("/{reading_id}/sessions", response_model=list[ReadingSessionItem])
async def list_reading_sessions(
    reading_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[ReadingSessionItem]:
    """The student's past sessions on this reading, newest first."""
    rows = await review_service.list_sessions_for_reading(db, user.id, reading_id)
    return [ReadingSessionItem(**row) for row in rows]
