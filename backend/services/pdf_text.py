"""Turn an uploaded PDF into the plain text the agents will grade against.

The instructor reviews and corrects this text before the reading is saved, so it
does not have to be perfect. It has to be a good starting point: paragraphs kept
as paragraphs, and as little noise as possible for the instructor to clean up.

A PDF has no paragraphs, only positioned lines, so they are rebuilt from the
layout. A gap between two lines noticeably larger than the usual line spacing
starts a new paragraph. Lines of the same height sitting side by side, as in a
table row, are joined into one.

Short labels drawn inside a diagram ("net", "B", "about 1 m") are dropped: they
read as noise out of context, and the figure's description replaces them. Only
short lines are dropped, so running text over a shaded box survives. Losing real
text silently would be worse than leaving the instructor a stray label to delete.

pdfminer.six rather than pypdf because pypdf returns text without positions,
which leaves nothing to rebuild paragraphs from.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from io import BytesIO

from pdfminer.high_level import extract_pages
from pdfminer.layout import (
    LAParams,
    LTCurve,
    LTFigure,
    LTImage,
    LTLine,
    LTTextContainer,
    LTTextLine,
)
from pdfminer.pdfparser import PDFSyntaxError

#: Lines of at most this many words inside a diagram are treated as its labels.
LABEL_MAX_WORDS = 4
#: Graphics closer than this (points) belong to the same diagram.
MERGE_GAP = 12
#: Labels sit beside a drawing as often as on it, so a label this far outside
#: the drawn area still counts as the diagram's.
LABEL_REACH = 30
#: A diagram smaller than this in both directions is decoration, not a figure.
MIN_FIGURE_SIDE = 40
#: How much larger than the usual line spacing a gap must be to break a paragraph.
PARAGRAPH_GAP = 1.35

_ENDS_SENTENCE = re.compile(r"[.!?:;\"'”’)\]]$")


class NotAPdf(Exception):
    """The bytes are not a PDF pdfminer can open."""


@dataclass
class _Line:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float

    @property
    def height(self) -> float:
        return self.top - self.bottom


@dataclass
class _Box:
    x0: float
    y0: float
    x1: float
    y1: float

    def near(self, other: _Box) -> bool:
        return not (
            other.x0 > self.x1 + MERGE_GAP
            or other.x1 < self.x0 - MERGE_GAP
            or other.y0 > self.y1 + MERGE_GAP
            or other.y1 < self.y0 - MERGE_GAP
        )

    def absorb(self, other: _Box) -> None:
        self.x0, self.y0 = min(self.x0, other.x0), min(self.y0, other.y0)
        self.x1, self.y1 = max(self.x1, other.x1), max(self.y1, other.y1)

    def reaches(self, x: float, y: float) -> bool:
        return (
            self.x0 - LABEL_REACH <= x <= self.x1 + LABEL_REACH
            and self.y0 - LABEL_REACH <= y <= self.y1 + LABEL_REACH
        )


def extract_pages_text(data: bytes) -> list[list[str]]:
    """Each page's paragraphs, in reading order. Empty lists for pages with no text.

    Raises NotAPdf if the bytes cannot be parsed as a PDF.
    """
    try:
        layouts = list(extract_pages(BytesIO(data), laparams=LAParams()))
    except (PDFSyntaxError, ValueError, TypeError, KeyError) as e:
        raise NotAPdf from e
    except Exception as e:  # pdfminer raises a wide variety on malformed input
        raise NotAPdf from e

    pages = [_paragraphs(_rows(_lines(layout))) for layout in layouts]
    return _join_across_pages(pages)


def to_text(pages: list[list[str]]) -> str:
    """The pages' paragraphs as one text, a blank line between paragraphs."""
    return "\n\n".join(p for page in pages for p in page)


# --------------------------------------------------------------------------- #
# layout


def _figure_regions(layout) -> list[_Box]:
    """Areas of the page covered by drawings or images.

    Straight lines are left out: those are table rules and underlines, and the
    text between them is content.
    """
    boxes: list[_Box] = []
    for el in _walk(layout):
        if isinstance(el, LTLine):
            continue
        if isinstance(el, (LTCurve, LTImage, LTFigure)):
            if el.width > 3 and el.height > 3 or isinstance(el, (LTImage, LTFigure)):
                boxes.append(_Box(el.x0, el.y0, el.x1, el.y1))

    merged: list[_Box] = []
    for box in boxes:
        for region in merged:
            if region.near(box):
                region.absorb(box)
                break
        else:
            merged.append(box)
    # One more pass, since absorbing can bring two regions within reach.
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(merged):
            for b in merged[i + 1 :]:
                if a.near(b):
                    a.absorb(b)
                    merged.remove(b)
                    changed = True
                    break
            if changed:
                break
    return [
        r for r in merged
        if r.x1 - r.x0 >= MIN_FIGURE_SIDE and r.y1 - r.y0 >= MIN_FIGURE_SIDE
    ]


def _walk(el):
    yield el
    if hasattr(el, "__iter__") and not isinstance(el, LTTextContainer):
        for child in el:
            yield from _walk(child)


def _lines(layout) -> list[_Line]:
    regions = _figure_regions(layout)
    out: list[_Line] = []
    for el in _walk(layout):
        if not isinstance(el, LTTextContainer):
            continue
        for line in el:
            if not isinstance(line, LTTextLine):
                continue
            text = " ".join(line.get_text().split())
            if not text or text.isdigit():  # empty, or a page number
                continue
            cx, cy = (line.x0 + line.x1) / 2, (line.y0 + line.y1) / 2
            if len(text.split()) <= LABEL_MAX_WORDS and any(
                r.reaches(cx, cy) for r in regions
            ):
                continue
            out.append(_Line(text, line.x0, line.x1, line.y1, line.y0))
    return out


def _rows(lines: list[_Line]) -> list[_Line]:
    """Merge lines sharing a baseline into one, left to right.

    A table row, or a running header split across the page. Cells far apart are
    separated with a bar so the columns stay readable as text.
    """
    lines = sorted(lines, key=lambda l: (-l.top, l.x0))
    rows: list[list[_Line]] = []
    for line in lines:
        if rows and abs(rows[-1][0].top - line.top) < min(line.height, rows[-1][0].height) * 0.5:
            rows[-1].append(line)
        else:
            rows.append([line])

    merged: list[_Line] = []
    for row in rows:
        row.sort(key=lambda l: l.x0)
        text = row[0].text
        for prev, cur in zip(row, row[1:]):
            text += (" | " if cur.x0 - prev.x1 > 20 else " ") + cur.text
        merged.append(
            _Line(text, row[0].x0, row[-1].x1, max(l.top for l in row), min(l.bottom for l in row))
        )
    return merged


def _paragraphs(lines: list[_Line]) -> list[str]:
    if not lines:
        return []
    pitches = [
        a.top - b.top
        for a, b in zip(lines, lines[1:])
        if 0 < a.top - b.top < a.height * 3
    ]
    pitch = statistics.median(pitches) if pitches else lines[0].height * 1.2

    paragraphs: list[str] = []
    current = lines[0].text
    for prev, line in zip(lines, lines[1:]):
        gap = prev.top - line.top
        new_size = abs(line.height - prev.height) > max(line.height, prev.height) * 0.25
        if gap > pitch * PARAGRAPH_GAP or new_size:
            paragraphs.append(current)
            current = line.text
        else:
            current = _join(current, line.text)
    paragraphs.append(current)
    return paragraphs


def _join(left: str, right: str) -> str:
    """Join two wrapped lines, undoing a hyphen the line break introduced."""
    if left.endswith("-") and right[:1].islower():
        return left[:-1] + right
    return f"{left} {right}"


def _join_across_pages(pages: list[list[str]]) -> list[list[str]]:
    """A paragraph cut by a page break is put back together."""
    for i in range(len(pages) - 1):
        here, after = pages[i], pages[i + 1]
        if not here or not after:
            continue
        if not _ENDS_SENTENCE.search(here[-1]) and after[0][:1].islower():
            here[-1] = _join(here[-1], after.pop(0))
    return pages
