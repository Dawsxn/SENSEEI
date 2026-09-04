"""Reading endpoints: what a student can see, and one reading's detail.

Both are ordinary JSON reads scoped to the signed-in student. Visibility is
enforced in the service; the detail endpoint returns 404 for a reading the
student cannot see, so an unassigned id looks the same as a missing one.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..models import User
from ..schemas import ReadingDetail, ReadingListItem
from ..services import reading_service

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
