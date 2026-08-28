# Design sources

Screen and logo designs as static mockups. Not a prototype, and not the app.

Each `.dc.html` file is one artboard. `canvas.json` lays them out. Together they
assemble into a single pan-and-zoom canvas, which is what you actually look at.

**The assembled canvas is not committed.** It embeds a whole editor and runs to
about 2 MB per build, so `.gitignore` keeps `design/**/*.html` out while allowing
`design/**/*.dc.html` through. Edit the sources, then rebuild.

Rebuilding is done by the `/design` skill in Claude Code, which owns the assembly
step. Ask it to rebuild the canvas from the sources in this directory.

## What is here

`design/` holds the app screens, `design/logo/` holds logo explorations.

| Artboard | Screen |
| --- | --- |
| 1 | Sign in |
| 2 | Reading list |
| 3 | Reading detail, full page |
| 3b | Reading detail, dialog |
| 4 | Tutoring session |
| 4b | Tutoring session with a PDF reading |
| 5 | Session review, student |
| 5b | Session review, instructor |

Several artboards carry a Scenario or State control above them, which switches
between cases rather than duplicating the artboard. Artboard 3 and 3b cover four
history states each; artboard 5 shows a complete session and 5b a failed one.

## Decisions these record

- **3b is the chosen direction** for reading detail. 3 is kept for comparison.
- **4b is a comparison, not a proposal.** It shows what rendering the reading as
  a PDF would buy and cost. The reasoning against it is in
  `docs/context/data-model.md`.
- **The logo is unresolved.** The mark used across the screens is direction A
  from `design/logo/`, standing in as a placeholder. The wordmark sets SEE-I in
  the accent colour, since the framework name sits inside the product name.

## Relationship to the design system

`docs/context/design-system.md` is authoritative for tokens and component
conventions. These files should follow it, not the other way round.

The mockups are hand-written HTML that imitates shadcn, because artboards cannot
run React. Where a mockup and a real shadcn component disagree, the component
wins. The mockups specify layout, copy, states and behaviour, not component
internals.
