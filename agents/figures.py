"""Describe a reading's figures in words, once, when the instructor uploads it.

This is an upload tool, not a third agent. It runs once per upload, never talks
to a student, and a human reads and corrects every word it writes before the
reading is saved. It exists because the tutor only ever sees a reading's text,
while the student sees its figures: a figure nobody described is something a
student can cite and the Assessment Agent has never seen.

It returns descriptions and where they belong. Placing them in the text is the
caller's job, since only the caller has the text laid out.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

#: Sent with the extracted text, so the model can quote captions exactly.
_USER_PROMPT = """# EXTRACTED TEXT
{text}

# TASK
Describe the figures in the attached PDF, following the instructions."""


@dataclass
class Figure:
    description: str
    label: str | None = None
    caption: str | None = None
    page: int | None = None


@dataclass
class FigureResult:
    figures: list[Figure] = field(default_factory=list)
    error: str = ""
    usage: dict | None = None

    @property
    def ok(self) -> bool:
        return not self.error


class FigureDescriber:
    def __init__(self, provider, system_prompt: str):
        self.provider = provider
        self.system_prompt = system_prompt

    def describe(self, pdf: bytes, extracted_text: str) -> FigureResult:
        """Never raises. A failure is reported in `error`, and the upload goes on
        without descriptions: the instructor is told, and can write them."""
        try:
            raw = self.provider.complete_with_file(
                self.system_prompt,
                _USER_PROMPT.format(text=extracted_text),
                pdf,
                "application/pdf",
            )
        except Exception as e:  # the provider's errors are many and unimportant here
            return FigureResult(error=f"{type(e).__name__}: {e}")
        usage = getattr(self.provider, "last_usage", None)
        try:
            return FigureResult(figures=parse_figures(raw), usage=usage)
        except ValueError as e:
            return FigureResult(error=str(e), usage=usage)


def parse_figures(raw: str) -> list[Figure]:
    """The model's JSON as figures. Entries without a description are skipped."""
    text = raw.strip()
    # Tolerate a fenced block, which models add even when asked for bare JSON.
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"not JSON: {e}") from e
    items = data.get("figures") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("no figures list")

    figures = []
    for item in items:
        if not isinstance(item, dict):
            continue
        description = " ".join(str(item.get("description") or "").split())
        if not description:
            continue
        page = item.get("page")
        figures.append(
            Figure(
                description=description,
                label=_clean(item.get("label")),
                caption=_clean(item.get("caption")),
                page=page if isinstance(page, int) and page > 0 else None,
            )
        )
    return figures


def _clean(value) -> str | None:
    text = " ".join(str(value).split()) if value is not None else ""
    return text or None
