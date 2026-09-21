"""Class endpoints: an instructor's classes, and a student joining one.

The instructor routes are all scoped to classes the signed-in instructor owns,
and one that is not theirs is a 404, the same as one that does not exist. The
single student route is joining by code.

The instructor routes live under `/instructor`, not at `/classes`, because
`/classes` is the address of the instructor's page. The pages and the API share
one origin, so an API path that matches a page path answers a refreshed or
bookmarked page with JSON.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import require_instructor, require_student
from ..models import User
from ..schemas import (
    ClassDetailOut,
    ClassIn,
    ClassListItem,
    JoinCodeOut,
    JoinIn,
    JoinOut,
)
from ..services import class_service
from ..services.class_service import (
    ClassNotFound,
    DuplicateClass,
    Fields,
    UnknownCode,
)

router = APIRouter(tags=["classes"])

NOT_FOUND = HTTPException(status_code=404, detail="class not found")
DUPLICATE = HTTPException(
    status_code=409, detail="you already have a class with that name and section"
)


@router.get("/instructor/classes", response_model=list[ClassListItem])
async def list_classes(
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> list[ClassListItem]:
    rows = await class_service.list_classes(db, user.id)
    return [ClassListItem(**row) for row in rows]


@router.post("/instructor/classes", response_model=ClassListItem, status_code=201)
async def create_class(
    body: ClassIn,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> ClassListItem:
    try:
        row = await class_service.create_class(
            db, user.id, Fields(body.name, body.section)
        )
    except DuplicateClass:
        raise DUPLICATE
    return ClassListItem(**row)


@router.get("/instructor/classes/{class_id}", response_model=ClassDetailOut)
async def get_class(
    class_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> ClassDetailOut:
    try:
        return ClassDetailOut(**await class_service.get_class(db, user.id, class_id))
    except ClassNotFound:
        raise NOT_FOUND


@router.patch("/instructor/classes/{class_id}", response_model=ClassDetailOut)
async def update_class(
    class_id: uuid.UUID,
    body: ClassIn,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> ClassDetailOut:
    try:
        row = await class_service.update_class(
            db, user.id, class_id, Fields(body.name, body.section)
        )
    except ClassNotFound:
        raise NOT_FOUND
    except DuplicateClass:
        raise DUPLICATE
    return ClassDetailOut(**row)


@router.delete("/instructor/classes/{class_id}", status_code=204)
async def delete_class(
    class_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> Response:
    try:
        await class_service.delete_class(db, user.id, class_id)
    except ClassNotFound:
        raise NOT_FOUND
    return Response(status_code=204)


@router.post("/instructor/classes/{class_id}/join-code", response_model=JoinCodeOut)
async def replace_join_code(
    class_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> JoinCodeOut:
    try:
        row = await class_service.replace_join_code(db, user.id, class_id)
    except ClassNotFound:
        raise NOT_FOUND
    return JoinCodeOut(join_code=row["join_code"])


@router.delete("/instructor/classes/{class_id}/students/{student_id}", status_code=204)
async def remove_student(
    class_id: uuid.UUID,
    student_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> Response:
    try:
        await class_service.remove_student(db, user.id, class_id, student_id)
    except ClassNotFound:
        raise NOT_FOUND
    return Response(status_code=204)


@router.post("/enrolments", response_model=JoinOut)
async def join_class(
    body: JoinIn,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> JoinOut:
    """Join a class by its code. Unknown codes and deleted classes are one 404."""
    try:
        return JoinOut(**await class_service.join_class(db, user.id, body.join_code))
    except UnknownCode:
        raise HTTPException(status_code=404, detail="no class with that code")
