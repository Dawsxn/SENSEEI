"""An instructor's readings: uploading one, and managing it afterwards.

Upload is two calls. The first turns the PDF into text and describes its
figures, and saves nothing: the instructor then reads and corrects that text,
because it is what every agent will grade against. The second saves the reading
with the text as corrected, its core components and its classes, all at once.
Leaving between the two leaves nothing behind.

After saving, the text and core components are locked. Changing either would
change what earlier sessions on the reading were graded against, so this module
has no way to do it. Title, description and classes stay editable: they change
how the reading is shown and who sees it, never what it says.

Like classes, a reading that is not the instructor's is reported exactly as one
that does not exist, and deleting is soft.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.figures import Figure, FigureDescriber

from ..models import (
    Class,
    CoreComponent,
    Reading,
    ReadingAssignment,
    ReadingFile,
    Session,
    SessionStatus,
    class_label,
    utcnow,
)
from .pdf_text import NotAPdf, extract_pages_text, to_text

MAX_BYTES = 20 * 1024 * 1024


class NotPdf(Exception):
    """The upload is not a PDF."""


class TooLarge(Exception):
    """The upload is over MAX_BYTES."""


class NoText(Exception):
    """The PDF has no text to extract, usually because it is a scanned image."""


class ReadingNotFound(Exception):
    """No such reading, or not this instructor's. Deliberately the same thing."""


class UnknownClass(Exception):
    """A class id that is not one of this instructor's live classes."""


@dataclass
class NewReading:
    title: str
    description: str | None
    content: str
    core_components: list[str]
    class_ids: list[uuid.UUID]
    filename: str
    pdf: bytes


# --------------------------------------------------------------------------- #
# step one: the PDF to text, nothing saved


def check_pdf(data: bytes) -> None:
    if len(data) > MAX_BYTES:
        raise TooLarge
    # The spec allows the header anywhere in the first kilobyte.
    if b"%PDF-" not in data[:1024]:
        raise NotPdf


async def extract(data: bytes, describer: FigureDescriber) -> dict:
    """The PDF's text with its figures described in place, for the instructor to
    check. Figure descriptions failing is not an error: the text comes back
    without them and `figures_failed` says so."""
    check_pdf(data)
    try:
        # pdfminer and the provider call both block; neither may hold the loop.
        pages = await asyncio.to_thread(extract_pages_text, data)
    except NotAPdf as e:
        raise NotPdf from e
    text = to_text(pages)
    if not text.strip():
        raise NoText

    result = await asyncio.to_thread(describer.describe, data, text)
    if not result.ok:
        return {"text": text, "figures_described": 0, "figures_failed": True}
    return {
        "text": to_text(place_figures(pages, result.figures)),
        "figures_described": len(result.figures),
        "figures_failed": False,
    }


def place_figures(pages: list[list[str]], figures: list[Figure]) -> list[list[str]]:
    """Put each description in the text, just before its caption.

    The caption is found by its opening words, since the extracted paragraph
    usually runs on past the caption's first line. A figure whose caption cannot
    be found goes at the end of its page, or of the reading if its page is
    unknown: roughly placed beats dropped, and the instructor sees it either way.
    """
    pages = [list(p) for p in pages]
    for n, fig in enumerate(figures, start=1):
        line = f"[{fig.label or f'Figure {n}'}: {fig.description}]"
        spot = _find_caption(pages, fig)
        if spot is not None:
            page, index = spot
            pages[page].insert(index, line)
        elif fig.page is not None and fig.page <= len(pages):
            pages[fig.page - 1].append(line)
        elif pages:
            pages[-1].append(line)
    return pages


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _find_caption(pages: list[list[str]], fig: Figure) -> tuple[int, int] | None:
    if not fig.caption:
        return None
    needle = _norm(fig.caption)[:40]
    if not needle:
        return None
    order = range(len(pages))
    if fig.page is not None and fig.page <= len(pages):
        # Its own page first, then everywhere, in case the page number is off.
        order = [fig.page - 1, *[i for i in order if i != fig.page - 1]]
    for p in order:
        for i, paragraph in enumerate(pages[p]):
            if _norm(paragraph).startswith(needle):
                return p, i
    return None


# --------------------------------------------------------------------------- #
# step two: save


async def _live_classes(
    db: AsyncSession, instructor_id: uuid.UUID, class_ids: list[uuid.UUID]
) -> list[uuid.UUID]:
    wanted = list(dict.fromkeys(class_ids))
    if not wanted:
        return []
    found = set(
        await db.scalars(
            select(Class.id).where(
                Class.id.in_(wanted),
                Class.instructor_id == instructor_id,
                Class.deleted_at.is_(None),
            )
        )
    )
    if len(found) != len(wanted):
        raise UnknownClass
    return wanted


async def create_reading(
    db: AsyncSession, instructor_id: uuid.UUID, new: NewReading
) -> uuid.UUID:
    """Save a reading with its file, core components and classes, in one commit."""
    check_pdf(new.pdf)
    class_ids = await _live_classes(db, instructor_id, new.class_ids)

    reading = Reading(
        uploaded_by=instructor_id,
        title=new.title,
        description=new.description,
        content=new.content,
    )
    db.add(reading)
    await db.flush()
    db.add_all(
        CoreComponent(reading_id=reading.id, text=text, position=i)
        for i, text in enumerate(new.core_components, start=1)
    )
    db.add(
        ReadingFile(
            reading_id=reading.id,
            filename=new.filename,
            media_type="application/pdf",
            byte_size=len(new.pdf),
            data=new.pdf,
        )
    )
    db.add_all(
        ReadingAssignment(reading_id=reading.id, class_id=cid) for cid in class_ids
    )
    await db.commit()
    return reading.id


# --------------------------------------------------------------------------- #
# reads


async def _owned(db: AsyncSession, instructor_id: uuid.UUID, reading_id: uuid.UUID) -> Reading:
    reading = await db.scalar(
        select(Reading).where(
            Reading.id == reading_id,
            Reading.uploaded_by == instructor_id,
            Reading.deleted_at.is_(None),
        )
    )
    if reading is None:
        raise ReadingNotFound
    return reading


async def _classes_of(db: AsyncSession, reading_ids: list[uuid.UUID]) -> dict:
    """Each reading's live classes, as (id, label), sorted by label."""
    rows = await db.execute(
        select(ReadingAssignment.reading_id, Class.id, class_label())
        .join(Class, Class.id == ReadingAssignment.class_id)
        .where(
            ReadingAssignment.reading_id.in_(reading_ids),
            ReadingAssignment.deleted_at.is_(None),
            Class.deleted_at.is_(None),
        )
        .order_by(class_label())
    )
    out: dict[uuid.UUID, list[dict]] = {rid: [] for rid in reading_ids}
    for reading_id, class_id, label in rows:
        out[reading_id].append({"id": class_id, "label": label})
    return out


async def list_readings(db: AsyncSession, instructor_id: uuid.UUID) -> list[dict]:
    """The instructor's readings, newest first.

    Sessions counts finished ones only. One still in progress may yet be
    abandoned, and until the discard flow exists would linger in the count.
    """
    sessions = (
        select(func.count())
        .select_from(Session)
        .where(
            Session.reading_id == Reading.id,
            Session.status.in_(
                [SessionStatus.COMPLETE.value, SessionStatus.FALLBACK.value]
            ),
        )
        .scalar_subquery()
    )
    rows = (
        await db.execute(
            select(Reading, sessions)
            .where(Reading.uploaded_by == instructor_id, Reading.deleted_at.is_(None))
            .order_by(Reading.created_at.desc())
        )
    ).all()
    classes = await _classes_of(db, [r.id for r, _ in rows])
    return [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "classes": [c["label"] for c in classes[r.id]],
            "session_count": count,
            "created_at": r.created_at,
        }
        for r, count in rows
    ]


async def get_reading(
    db: AsyncSession, instructor_id: uuid.UUID, reading_id: uuid.UUID
) -> dict:
    reading = await _owned(db, instructor_id, reading_id)
    components = await db.scalars(
        select(CoreComponent.text)
        .where(CoreComponent.reading_id == reading_id)
        .order_by(CoreComponent.position)
    )
    has_file = await db.scalar(
        select(ReadingFile.id).where(ReadingFile.reading_id == reading_id)
    )
    return {
        "id": reading.id,
        "title": reading.title,
        "description": reading.description,
        "content": reading.content,
        "core_components": list(components),
        "classes": (await _classes_of(db, [reading_id]))[reading_id],
        "has_file": has_file is not None,
        "created_at": reading.created_at,
    }


async def get_file(
    db: AsyncSession, instructor_id: uuid.UUID, reading_id: uuid.UUID
) -> ReadingFile:
    await _owned(db, instructor_id, reading_id)
    file = await db.scalar(select(ReadingFile).where(ReadingFile.reading_id == reading_id))
    if file is None:
        raise ReadingNotFound
    return file


# --------------------------------------------------------------------------- #
# writes after saving: never the text or the core components


async def update_reading(
    db: AsyncSession,
    instructor_id: uuid.UUID,
    reading_id: uuid.UUID,
    title: str,
    description: str | None,
) -> dict:
    reading = await _owned(db, instructor_id, reading_id)
    reading.title, reading.description = title, description
    await db.commit()
    return await get_reading(db, instructor_id, reading_id)


async def set_classes(
    db: AsyncSession,
    instructor_id: uuid.UUID,
    reading_id: uuid.UUID,
    class_ids: list[uuid.UUID],
) -> dict:
    """Make the reading's classes exactly these.

    A class taken off is soft-deleted rather than removed, like every other
    assignment change, so a class put back gets a fresh row and the old one
    keeps the record of when it was assigned.
    """
    await _owned(db, instructor_id, reading_id)
    wanted = set(await _live_classes(db, instructor_id, class_ids))
    current = list(
        await db.scalars(
            select(ReadingAssignment).where(
                ReadingAssignment.reading_id == reading_id,
                ReadingAssignment.deleted_at.is_(None),
            )
        )
    )
    now = utcnow()
    for row in current:
        if row.class_id not in wanted:
            row.deleted_at = now
    have = {row.class_id for row in current}
    db.add_all(
        ReadingAssignment(reading_id=reading_id, class_id=cid)
        for cid in wanted - have
    )
    await db.commit()
    return await get_reading(db, instructor_id, reading_id)


async def delete_reading(
    db: AsyncSession, instructor_id: uuid.UUID, reading_id: uuid.UUID
) -> None:
    """Soft delete. Students lose the reading; its sessions stay in the data."""
    reading = await _owned(db, instructor_id, reading_id)
    reading.deleted_at = utcnow()
    await db.commit()
