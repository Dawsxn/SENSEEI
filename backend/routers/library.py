"""An instructor's readings: upload, then manage.

Upload is two calls, `extract` then `create`, with the instructor correcting the
text in between. See `library_service` for why nothing is saved until the second.

Under `/instructor/readings` rather than `/readings`, which is the students'
API. The instructor's pages are at `/library` for the same reason `/classes` is
not an API path: pages and API share one origin, so a page path that is also an
API path answers a refresh with JSON.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from agents.figures import FigureDescriber

from ..db import get_session
from ..deps import get_figure_describer_dep, require_instructor
from ..models import User
from ..schemas import (
    ExtractOut,
    LibraryItem,
    LibraryReading,
    ReadingClassesIn,
    ReadingCreatedOut,
    ReadingEditIn,
)
from ..services import library_service
from ..services.library_service import (
    MAX_BYTES,
    NewReading,
    NoText,
    NotPdf,
    ReadingNotFound,
    TooLarge,
    UnknownClass,
)

router = APIRouter(prefix="/instructor/readings", tags=["library"])

NOT_FOUND = HTTPException(status_code=404, detail="reading not found")
# The frontend keys its messages off these codes, not the wording.
NOT_PDF = HTTPException(status_code=415, detail="not_pdf")
TOO_LARGE = HTTPException(status_code=413, detail="too_large")
NO_TEXT = HTTPException(status_code=422, detail="no_text")
UNKNOWN_CLASS = HTTPException(status_code=422, detail="unknown_class")


async def _read(file: UploadFile) -> bytes:
    """The upload's bytes, refusing early rather than holding an oversized file."""
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise TOO_LARGE
    return data


@router.get("", response_model=list[LibraryItem])
async def list_readings(
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> list[LibraryItem]:
    return [LibraryItem(**row) for row in await library_service.list_readings(db, user.id)]


@router.post("/extract", response_model=ExtractOut)
async def extract(
    file: UploadFile = File(...),
    user: User = Depends(require_instructor),
    describer: FigureDescriber = Depends(get_figure_describer_dep),
) -> ExtractOut:
    """The PDF as text with its figures described. Saves nothing."""
    data = await _read(file)
    try:
        return ExtractOut(**await library_service.extract(data, describer))
    except NotPdf:
        raise NOT_PDF
    except TooLarge:
        raise TOO_LARGE
    except NoText:
        raise NO_TEXT


@router.post("", response_model=ReadingCreatedOut, status_code=201)
async def create_reading(
    file: UploadFile = File(...),
    title: str = Form(..., max_length=200),
    description: str | None = Form(None, max_length=200),
    content: str = Form(...),
    core_components: list[str] = Form(...),
    class_ids: list[uuid.UUID] = Form(default=[]),
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> ReadingCreatedOut:
    """Save the reading with the text as the instructor corrected it."""
    components = [c.strip() for c in core_components if c.strip()]
    if not components:
        raise HTTPException(status_code=422, detail="no_core_components")
    if not title.strip() or not content.strip():
        raise HTTPException(status_code=422, detail="missing_fields")
    new = NewReading(
        title=title.strip(),
        description=(description or "").strip() or None,
        content=content.strip(),
        core_components=components,
        class_ids=class_ids,
        filename=file.filename or "reading.pdf",
        pdf=await _read(file),
    )
    try:
        reading_id = await library_service.create_reading(db, user.id, new)
    except NotPdf:
        raise NOT_PDF
    except TooLarge:
        raise TOO_LARGE
    except UnknownClass:
        raise UNKNOWN_CLASS
    return ReadingCreatedOut(id=reading_id)


@router.get("/{reading_id}", response_model=LibraryReading)
async def get_reading(
    reading_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> LibraryReading:
    try:
        return LibraryReading(**await library_service.get_reading(db, user.id, reading_id))
    except ReadingNotFound:
        raise NOT_FOUND


@router.get("/{reading_id}/file")
async def get_reading_file(
    reading_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> Response:
    try:
        file = await library_service.get_file(db, user.id, reading_id)
    except ReadingNotFound:
        raise NOT_FOUND
    return Response(
        content=file.data,
        media_type=file.media_type,
        headers={
            "Content-Disposition": f'inline; filename="{file.filename}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.patch("/{reading_id}", response_model=LibraryReading)
async def update_reading(
    reading_id: uuid.UUID,
    body: ReadingEditIn,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> LibraryReading:
    """Title and description only. The text and core components are locked."""
    try:
        row = await library_service.update_reading(
            db, user.id, reading_id, body.title, body.description
        )
    except ReadingNotFound:
        raise NOT_FOUND
    return LibraryReading(**row)


@router.put("/{reading_id}/classes", response_model=LibraryReading)
async def set_classes(
    reading_id: uuid.UUID,
    body: ReadingClassesIn,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> LibraryReading:
    try:
        row = await library_service.set_classes(db, user.id, reading_id, body.class_ids)
    except ReadingNotFound:
        raise NOT_FOUND
    except UnknownClass:
        raise UNKNOWN_CLASS
    return LibraryReading(**row)


@router.delete("/{reading_id}", status_code=204)
async def delete_reading(
    reading_id: uuid.UUID,
    user: User = Depends(require_instructor),
    db: AsyncSession = Depends(get_session),
) -> Response:
    try:
        await library_service.delete_reading(db, user.id, reading_id)
    except ReadingNotFound:
        raise NOT_FOUND
    return Response(status_code=204)
