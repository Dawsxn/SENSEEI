# Design sources

Screen and logo designs as static mockups. Not a prototype, and not the app.

Each `.dc.html` file is one artboard. `canvas.json` lays them out. Together they
assemble into a single pan-and-zoom canvas, which is what you actually look at.

**The assembled canvas is not committed.** It embeds a whole editor and runs to
about 2 MB per build, so `.gitignore` keeps `design/**/*.html` out while allowing
`design/**/*.dc.html` through. Edit the sources, then rebuild.

Rebuilding is done by the `/design` skill in Claude Code, which owns the assembly
step. Ask it to rebuild the canvas from the sources in this directory.

To regenerate a single PNG without building the whole canvas:

```
python scripts/render_artboard.py design/ReadingStep.dc.html design/png/03c-reading-step.png 1440 900 "state=Reading"
```

## The screens

Click any of these to view it. `png/` is regenerated from the sources whenever a
design changes, so it always matches.

| Screen | Image |
| --- | --- |
| Sign in | [png/01-sign-in.png](png/01-sign-in.png) |
| Reading list | [png/02-reading-list.png](png/02-reading-list.png) |
| Reading detail, full page | [png/03-reading-detail.png](png/03-reading-detail.png) |
| Reading detail, dialog | [png/03b-reading-detail-dialog.png](png/03b-reading-detail-dialog.png) |
| Reading step, intro dialog | [png/03c-reading-step-intro.png](png/03c-reading-step-intro.png) |
| Reading step | [png/03c-reading-step.png](png/03c-reading-step.png) |
| Reading step, text fallback | [png/03c-reading-step-text.png](png/03c-reading-step-text.png) |
| Tutoring session | [png/04-tutoring-session.png](png/04-tutoring-session.png) |
| Tutoring session, PDF reading | [png/04b-tutoring-pdf-reading.png](png/04b-tutoring-pdf-reading.png) |
| Criterion feedback, six approaches | [png/04c-criterion-feedback.png](png/04c-criterion-feedback.png) |
| Reference panel, components | [png/04d-panel-components.png](png/04d-panel-components.png) |
| Reference panel, rubric | [png/04d-panel-rubric.png](png/04d-panel-rubric.png) |
| Session review, student | [png/05-session-review.png](png/05-session-review.png) |
| Session review, instructor | [png/05b-session-review-instructor.png](png/05b-session-review-instructor.png) |

Do not open a `.dc.html` in a browser expecting to see the screen. It renders a
grey skeleton with `{{placeholder}}` text, because repeated rows and every
colour come from template values the canvas runtime supplies, and `support.js`
is not in this repository. The PNGs are what the screens look like.

## What is here

`design/` holds the app screens, `design/logo/` holds logo explorations.

Several artboards carry a Scenario or State control above them, which switches
between cases rather than duplicating the artboard. Artboard 3 and 3b cover four
history states each; 3c covers its opening dialog, a reading with a stored PDF,
and one without;
artboard 5 shows a complete session and 5b a failed one.

## Decisions these record

- **3b is the chosen direction** for reading detail. 3 is kept for comparison.
- **4b is shipped, not a comparison.** It was drawn as one, arguing that storing
  only the extracted text was enough. That argument rested on the agents being
  the only readers, which stopped being true once the student reads the document
  itself. `docs/context/data-model.md` records the reversal.
- **4c chose A**, tags under the message. The Tutor Agent stops naming the
  criteria in its prose as of prompt v2, so the interface labels them instead.
  The other five are kept because the comparison is the argument: C and D cost
  nothing on the backend, and losing that would make A look free.
- **4d is where the vocabulary is explained.** Tags carry only names, which is
  affordable because the rubric panel carries what each one asks for, in the
  rubric's own words.
- **3c is the step the app used to skip.** `student-tutoring-loop.md` has always
  called for the student to read first and say so explicitly; the earlier
  mockups folded that into the split screen.
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
