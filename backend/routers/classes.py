"""Class endpoints: an instructor's classes, and a student joining one.

The instructor routes are all scoped to classes the signed-in instructor owns,
and one that is not theirs is a 404, the same as one that does not exist. The
student routes are joining by code and reading the classes joined.

The instructor routes live under `/instructor`, not at `/classes`, because
`/classes` is the address of the instructor's page. The pages and the API share
one origin, so an API path that matches a page path answers a refreshed or
bookmarked page with JSON. For the same reason a student's classes are read
from `/enrolments`, where joining one already lives.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import require_instructor, require_student
from ..models import ClassMode, User
from ..schemas import (
    ClassDashboardOut,
    ClassDetailOut,
    ClassIn,
    ClassListItem,
    ClassReadingOut,
    JoinCodeOut,
    JoinIn,
    JoinOut,
    StudentClassDetail,
    StudentClassItem,
)
from ..services import analytics_service, class_service, library_service, reading_service
from ..services.analytics_service import ReadingNotInClass
from ..services.class_service import (
    ClassNotFound,
    DuplicateClass,
    Fields,
    ModeLocked,
    TestNotAvailable,
    UnknownCode,
)
from ..settings import get_settings

router = APIRouter(tags=["classes"])

NOT_FOUND = HTTPException(status_code=404, detail="class not found")
DUPLICATE = HTTPException(
    status_code=409, detail="you already have a class with that name and section"
)
MODE_LOCKED = HTTPException(
    status_code=409, detail="a participant has signed in, so the mode cannot change"
)
NO_SUCH_TEST = HTTPException(
    status_code=422, detail="that test is not for any of this class's readings"
)


class AddReadingsIn(BaseModel):
    reading_ids: list[uuid.UUID]


def _fields(body: ClassIn) -> Fields:
    """The class as typed. The control groups' modes exist only in trial mode."""
    if body.mode is not ClassMode.SEEI and not get_settings().trial_mode:
        raise HTTPException(status_code=422, detail="only SEE-I classes outside the trial")
    if body.test_key is not None and not get_settings().trial_mode:
        raise HTTPException(status_code=422, detail="tests exist only in the trial")
    return Fields(body.name, body.section, body.mode, body.test_key)


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
        row = await class_service.create_class(db, user.id, _fields(body))
    except DuplicateClass:
        raise DUPLICATE
    except TestNotAvailable:
        raise NO_SUCH_TEST
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
        row = await class_service.update_class(db, user.id, class_id, _fields(body))
    except ClassNotFound:
        raise NOT_FOUND
    except DuplicateClass:
        raise DUPLICATE
    except ModeLocked:
        raise MODE_LOCKED
    except TestNotAvailable:
        raise NO_SUCH_TEST
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


@router.get("/instructor/classes/{class_id}/statistics", response_model=ClassDashboardOut)
async def class_statistics(
    class_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> ClassDashboardOut:
    """The class's three statistics, and its readings with a session count each."""
    try:
        row = await analytics_service.class_dashboard(db, user.id, class_id)
    except ClassNotFound:
        raise NOT_FOUND
    return ClassDashboardOut(**row)


@router.get(
    "/instructor/classes/{class_id}/readings/{reading_id}",
    response_model=ClassReadingOut,
)
async def reading_in_class(
    class_id: uuid.UUID,
    reading_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> ClassReadingOut:
    """One reading inside one class: its statistics, and how far each student got.

    A reading that exists but is not assigned to this class is a 404, like one
    that does not exist: this page is about a reading *in* a class.
    """
    try:
        row = await analytics_service.reading_in_class(db, user.id, class_id, reading_id)
    except (ClassNotFound, ReadingNotInClass):
        raise HTTPException(status_code=404, detail="reading not found in this class")
    return ClassReadingOut(**row)


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


@router.post("/instructor/classes/{class_id}/readings", status_code=204)
async def add_readings(
    class_id: uuid.UUID,
    body: AddReadingsIn,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> Response:
    """Add readings the instructor already has to this class."""
    try:
        await library_service.add_to_class(db, user.id, class_id, body.reading_ids)
    except library_service.UnknownClass:
        raise NOT_FOUND
    except library_service.ReadingNotFound:
        raise HTTPException(status_code=404, detail="reading not found")
    except library_service.ClassHasReading:
        raise HTTPException(status_code=409, detail="class_has_reading")
    return Response(status_code=204)


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


@router.get("/enrolments", response_model=list[StudentClassItem])
async def list_my_classes(
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> list[StudentClassItem]:
    """The classes this student is in, with how far they are through each."""
    return [StudentClassItem(**row) for row in await reading_service.list_classes(db, user.id)]


@router.get("/enrolments/{class_id}", response_model=StudentClassDetail)
async def get_my_class(
    class_id: uuid.UUID,
    user: User = Depends(require_student),
    db: AsyncSession = Depends(get_session),
) -> StudentClassDetail:
    """One class the student is in, with its readings. Any other class is a 404."""
    detail = await reading_service.get_class(db, user.id, class_id)
    if detail is None:
        raise NOT_FOUND
    return StudentClassDetail(**detail)


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
