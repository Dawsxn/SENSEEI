"""Render every instrument as one document, for the content-validity review.

Section 4.6.4 requires the pre-test, post-test Part A, and the SBA case to be
"reviewed for content validity by two RVRCOB faculty members prior to
administration". This produces what they read.

The point is that it is *generated from the served content*, not written
alongside it. A review document maintained by hand drifts from the survey, and a
review then certifies a document nobody sat — which is the failure this whole
approach exists to avoid. Regenerate it after any edit; it takes a second.

It shows the reviewers what participants will not see: which items are scored and
what the correct answer is, which are attention checks, and which post-test items
answer which pre-test items. Those are exactly the things a content-validity
review needs to judge, and they are invisible on the survey itself.

Usage::

    python -m study.instruments.review               # writes review.html
    python -m study.instruments.review out/doc.html  # or somewhere specific
    python -m study.instruments.review --example     # the worked example set

It writes the file itself rather than printing to stdout. On Windows a shell
redirect encodes stdout as cp1252, which mangles every em dash and section sign
in the document — and the reviewers would be the ones to find out.
"""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from .loader import CONTENT_DIR, EXAMPLE_DIR, load_all, readiness
from .schema import Instrument, Item, ItemType

STYLE = """
  body { font: 15px/1.6 Georgia, 'Times New Roman', serif; max-width: 46rem;
         margin: 2rem auto; padding: 0 1.2rem; color: #1c1a17; }
  h1 { font-size: 1.5rem; } h2 { font-size: 1.2rem; margin-top: 2.4rem;
       border-bottom: 1px solid #ddd; padding-bottom: .3rem; }
  .meta, .note { font-family: ui-sans-serif, system-ui, sans-serif;
                 font-size: .82rem; color: #666; }
  .note { background: #f6f4f0; border-left: 3px solid #c9c2b6;
          padding: .6rem .8rem; margin: .8rem 0; }
  .todo { background: #fdf2e7; border-left-color: #8a4b1f; color: #8a4b1f; }
  ol.items { padding-left: 1.4rem; }
  ol.items > li { margin-bottom: 1.3rem; }
  ul.options { list-style: none; padding-left: 0; margin: .4rem 0; }
  ul.options li { padding: .1rem 0; }
  .tag { font-family: ui-sans-serif, system-ui, sans-serif; font-size: .7rem;
         text-transform: uppercase; letter-spacing: .05em; background: #eef3f1;
         color: #2f5d50; padding: .1rem .4rem; border-radius: 3px;
         margin-left: .4rem; }
  .tag.check { background: #fdf2e7; color: #8a4b1f; }
  .answer { color: #2f5d50; font-weight: bold; }
  blockquote { border-left: 3px solid #ddd; margin-left: 0; padding-left: 1rem;
               white-space: pre-wrap; }
"""


def render(instruments: dict[str, Instrument] | None = None) -> str:
    """The whole review document, as standalone HTML."""
    instruments = instruments if instruments is not None else load_all()
    ordered = sorted(instruments.values(), key=lambda i: _order(i.id))

    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>SENSEE-I trial instruments — for review</title>",
        f"<style>{STYLE}</style></head><body>",
        "<h1>SENSEE-I trial instruments</h1>",
        f"<p class='meta'>Generated {date.today().isoformat()} from "
        f"<code>{CONTENT_DIR.name}/</code>. This is the content the tool serves; "
        "it is generated rather than transcribed, so the two cannot disagree.</p>",
        _readiness_block(instruments),
        "<p class='note'>For the reviewers: correct answers, attention checks, "
        "and pre-test pairings are shown here and hidden from participants. "
        "Please check that each item measures what it is meant to, that the "
        "wording is unambiguous, and that nothing can be answered without "
        "having read the text.</p>",
    ]

    for instrument in ordered:
        parts.append(_instrument_block(instrument))

    parts.append("</body></html>")
    return "\n".join(parts)


def _order(instrument_id: str) -> int:
    from .loader import INSTRUMENT_ORDER

    return (
        INSTRUMENT_ORDER.index(instrument_id)
        if instrument_id in INSTRUMENT_ORDER
        else len(INSTRUMENT_ORDER)
    )


def _readiness_block(instruments: dict[str, Instrument]) -> str:
    problems = readiness(instruments)
    if not problems:
        return (
            "<p class='note'>All instruments are written and marked reviewed.</p>"
        )
    rows = "".join(f"<li>{html.escape(p)}</li>" for p in problems)
    return f"<div class='note todo'><strong>Outstanding</strong><ul>{rows}</ul></div>"


def _instrument_block(instrument: Instrument) -> str:
    parts = [f"<h2>{html.escape(instrument.title)}</h2>"]

    meta = [
        f"<code>{html.escape(instrument.id)}</code>",
        f"version {instrument.version}",
        instrument.status.value,
    ]
    if instrument.scoring:
        meta.append(f"scoring: {instrument.scoring}")
    parts.append(f"<p class='meta'>{' &middot; '.join(meta)}</p>")

    if instrument.source:
        parts.append(f"<p class='note'>{html.escape(instrument.source)}</p>")

    if instrument.instructions.strip():
        parts.append(
            f"<blockquote>{html.escape(instrument.instructions.strip())}</blockquote>"
        )

    if instrument.stimulus.strip():
        parts.append("<p class='meta'>Case presented to the participant:</p>")
        parts.append(
            f"<blockquote>{html.escape(instrument.stimulus.strip())}</blockquote>"
        )

    if instrument.is_placeholder:
        parts.append(
            "<div class='note todo'>No content written yet. See the notes at the "
            "top of the YAML file for what belongs here.</div>"
        )
        return "\n".join(parts)

    parts.append("<ol class='items'>")
    for item in instrument.items:
        parts.append(_item_block(item))
    parts.append("</ol>")
    return "\n".join(parts)


def _item_block(item: Item) -> str:
    tags = []
    if item.is_attention_check:
        tags.append("<span class='tag check'>attention check</span>")
    if item.screening:
        tags.append("<span class='tag'>screening</span>")
    if item.pairs_with:
        tags.append(
            f"<span class='tag'>pairs with {html.escape(item.pairs_with)}</span>"
        )
    if item.polarity:
        tags.append(f"<span class='tag'>{item.polarity.value}</span>")
    if not item.required:
        tags.append("<span class='tag'>optional</span>")

    parts = [f"<li><strong>{html.escape(item.text)}</strong>{''.join(tags)}"]

    if item.help_text:
        parts.append(f"<div class='meta'>{html.escape(item.help_text)}</div>")

    if item.options:
        parts.append("<ul class='options'>")
        for option in item.options:
            marks = []
            if item.answer == option.id:
                marks.append("<span class='answer'>&larr; correct</span>")
            if item.attention_expected == option.id:
                marks.append("<span class='answer'>&larr; expected</span>")
            parts.append(
                f"<li>{html.escape(option.text)} {' '.join(marks)}</li>"
            )
        parts.append("</ul>")
    elif item.type is ItemType.LONG_TEXT:
        parts.append("<div class='meta'>[written response]</div>")
    else:
        parts.append("<div class='meta'>[short answer]</div>")

    parts.append("</li>")
    return "\n".join(parts)


def write(
    path: str | Path = "review.html",
    content_dir: str | Path | None = None,
) -> Path:
    """Render the document to ``path``, always as UTF-8. Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(load_all(content_dir)), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    import sys

    args = list(sys.argv[1:] if argv is None else argv)

    content_dir = None
    if "--example" in args:
        args.remove("--example")
        content_dir = EXAMPLE_DIR

    path = write(args[0] if args else "review.html", content_dir)
    print(f"Wrote {path.resolve()}")


if __name__ == "__main__":
    main()
