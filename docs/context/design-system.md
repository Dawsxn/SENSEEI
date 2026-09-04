# Design system

Foundations are settled and apply to every screen. Patterns accumulate one screen
at a time as the designs are worked through, so that section grows rather than
being written in advance.

Built on shadcn/ui defaults. Where a value below matches shadcn's own, that is
deliberate and it should not be changed without a reason.

## Foundations

### Colour

| Token | Value | Used for |
| --- | --- | --- |
| Background | `#ffffff` | Page and card surfaces |
| Foreground | `#09090b` | Primary text |
| Muted foreground | `#71717a` | Secondary text, metadata, labels |
| Placeholder | `#a1a1aa` | Empty input text, the faintest legible tier |
| Border | `#e4e4e7` | All hairlines, card edges, dividers |
| Muted surface | `#f4f4f5` | Filled areas: tab strips, inactive fills |
| Body text on fills | `#3f3f46` | Text inside muted surfaces |
| Primary | `#16a34a` | Primary buttons, success states, passed steps |
| Primary hover | `#15803d` | |

Failure states use a soft treatment rather than shadcn's solid destructive:
`#fef2f2` background, `#fecaca` border, `#b91c1c` text. Solid red reads as
punitive on a screen where a student has just been told they fell short.

Success badges mirror it: `#f0fdf4`, `#bbf7d0`, `#15803d`.

Everything structural is neutral. Green appears only on primary actions and
success, which is what keeps the interface quiet.

### Type

Geist, weights 400, 500 and 600.

| Role | Size | Weight | Tracking |
| --- | --- | --- | --- |
| Page title | 24px | 600 | -0.02em |
| Section or card title | 14px | 500 | |
| Body and UI | 14px | 400 | |
| Secondary and metadata | 13px | 400 | |
| Smallest label | 12px | 400 or 500 | |

The ramp is deliberately moderate, roughly 1.8x from largest to smallest.
Hierarchy comes from weight and colour rather than size. An earlier draft ran 62px
against 11px and read as a marketing page.

Reading content sits at 15px with 1.75 line height, the only place body type goes
above 14px.

### Space and shape

| Property | Value |
| --- | --- |
| Card radius | 8px |
| Control radius | 6px |
| Pill radius | 999px, badges only |
| Button height | 36px default, 32px small |
| Input height | 36px |
| Raised shadow | `0 1px 2px 0 rgba(0,0,0,0.05)` |
| Card padding | 20px |
| Page padding | 24px |
| Table row padding | 14px vertical, 16px horizontal |

Density is compact. Controls are 32px to 36px, not 44px. This is desktop
software used at a desk for long sittings, not a phone.

### Icons

Inline SVG only, stroke-based, 24px viewBox, `stroke-width` 2, round caps and
joins. Rendered at 13px to 15px inline. Never emoji, never text glyphs like an
arrow or a multiplication sign standing in for an icon.

Stroke colour is `#71717a` for icons beside muted text and `#a1a1aa` for
decorative chevrons.

### Shell

A single top bar, 56px, with a `#e4e4e7` bottom border. No sidebar. There are few
destinations and the tutoring screen needs the horizontal room.

## Using shadcn

The default answer to "what should this be built from" is a shadcn component.

1. **Check the registry before building anything.** If shadcn has it, use it.
   Most of what this app needs already exists there.
2. **Add components through the CLI**, `npx shadcn@latest add <name>`, so they
   arrive wired to the project's tokens rather than hand-copied.
3. **Use them as they come.** Restyle through tokens and Tailwind classes, not by
   rewriting internals. A component edited internally stops matching its own
   documentation, and the next person to touch it will assume it behaves as
   documented.
4. **When nothing fits exactly, compose from shadcn primitives** rather than
   inventing. The split-screen tutoring layout, the chat, and the reading pane
   are compositions of existing components and plain layout, not new components.
5. **Build something genuinely new only when composition fails**, and then mimic
   shadcn's anatomy: the same tokens, control heights, focus and disabled states,
   and the same variant naming, so it does not announce itself as foreign.

### The mockups are not the source of truth for components

The screens in `design/` are hand-written HTML that imitates shadcn, because
design artboards cannot run React. They will differ from the real components in
small ways: exact focus rings, transition timing, disabled treatment, internal
markup.

**Where a mockup and the real shadcn component disagree, the component wins.**
The mockups specify layout, copy, states and behaviour. They do not specify
component internals.

## Components in play

Drawn from shadcn. Anything not on this list is a new decision, not a default.

| Component | Where |
| --- | --- |
| `Button` | Default and outline variants, default and small sizes |
| `Card` | Grouping on pre-reading and sign-in |
| `Table` | Reading list, and later the instructor roster |
| `Tabs` | Class filter, and the SEE-I step progression |
| `Badge` | Status, and criteria that were not met |
| `Textarea` | Response input |
| `Accordion` | Session review transcript, collapsed per step |
| `Avatar` | Top bar |

## Patterns

Recorded as each screen settles. A pattern written before a screen exists is a
guess, and a guess in this file has the authority of a decision, so each entry is
added only once the screen it comes from is built.

### Tutoring chat

Established by the tutoring screen (`feat/chat-ui`), from
`design/png/04-tutoring-session.png`.

- **Split screen.** Reading on the left, chat on the right, each scrolling on its
  own. The reading stays visible the whole session.
- **The reading pane is only the text.** No title (it is in the top bar), and
  the core components are not pinned beside the chat. They are not hidden,
  though: the pre-reading screen shows them, and during the session they sit
  behind a **Components** button in the top bar, the same way the rubric does.
  Both are reference the student opens on demand rather than material forced into
  view. They are not an answer key — the core components are drawn from the
  reading the student is looking at, and the Own Words criterion fails a verbatim
  copy.
- **Student messages** are a right-aligned bubble in the success tint `#f0fdf4`
  with `#3f3f46` text. This is the one place the success green carries a meaning
  other than success; it reads as "your voice", and the mockup is deliberate
  about it. The Tutor never sits in a bubble — its prose is the screen's default
  voice, left-aligned foreground text.
- **The fallback message** uses the soft failure treatment (`#fef2f2` /
  `#fecaca` / `#b91c1c`), because it is the one message that marks a step the
  student did not pass.
- **Steps are dividers, not tabs.** Each step's exchange sits under a hairline
  divider labelled with the step name, which turns green with a check once the
  step passes. Overall progress is a four-segment bar in the top bar: green for
  passed, foreground for the current step, border-grey for the rest.
- **A streaming reply** shows a blinking caret at its end until the message
  completes, so a partial message is never mistaken for a finished one. Its text
  is revealed at a steady rate rather than in the model's raw chunks, so uneven
  streaming still reads smoothly.
- **Waiting for the tutor** always looks the same — a row of pulsing dots —
  whether it is the opening question or the pause after a submit while grading
  runs. There is no separate placeholder-text state.
- **Attempts show as three dots** on the active step's divider, where a passed
  step shows its check. The filled dot is the attempt now being made, so its
  position tells the student which of the three tries they are on. Subtle, in the
  divider rather than a label over the composer.
- **Responsive.** The two panes sit side by side from `lg` up. Below that a
  split does not fit, so one pane shows at a time behind a Reading / Chat toggle,
  defaulting to the chat. On a phone the top bar drops the progress bar and the
  Rubric label (its icon stays). The compact control sizes are kept; the app is
  still desk-first, it just no longer breaks on a narrow screen.

## Related

- `docs/context/tech-stack.md`, the libraries these sit on
- `docs/context/student-tutoring-loop.md`, the behaviour the screens serve
- `design/`, the screen sources themselves
