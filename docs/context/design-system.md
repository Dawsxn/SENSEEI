# Design system

Foundations are settled and apply to every screen. Patterns accumulate one screen
at a time as the designs are worked through, so that section grows rather than
being written in advance.

Built on shadcn/ui defaults. Where a value below matches shadcn's own, that is
deliberate and it should not be changed without a reason.

## Foundations

### Colour

The palette is the SENSEE-I brand, **Pastel playful**. The page is a pale mint
rather than white, text is a deep green-grey rather than near-black, and the
quiet fills are a slightly deeper mint. It is the same interface as before with
the clinical white-and-zinc taken out of it: students sit with this screen for a
long reading, and the softness is there to make that sitting easier, not to
decorate it.

| Token | Value | Used for |
| --- | --- | --- |
| Background | `#f4fbf7` | The page. Pale mint |
| Card | `#ffffff` | Cards, dialogs, popovers, inputs, tables, the reading pane |
| Foreground | `#2d3a33` | Primary text. Deep green-grey, 11.3:1 on the page |
| Muted foreground | `#56665d` | Secondary text, metadata, labels. 5.8:1 |
| Placeholder | `#83938a` | Empty input text and decorative chevrons, the faintest legible tier |
| Border / Input | `#d4ebdd` | All hairlines, card edges, dividers |
| Muted surface | `#e3f5ea` | Mint tint: tab strips, inactive fills, the avatar circle |
| Body on fills | `#3a4740` | Text inside a muted or tinted surface |
| Primary | `#1d8049` | Primary buttons, green text, passed steps. White on it is 5.0:1 |
| Primary hover | `#19713f` | |
| Ring | `#2fb36b` | Focus ring, in the logo's green |
| Brand mint | `#2fb36b` | The logo's green. Decorative only |
| Brand hat | `#fbbf24` | The sensei's hat yellow. Decorative only |

Everything structural is one family. Colour arrives only on primary actions and
success, which is what keeps the interface quiet. The mint page and its tint
carry the softness; nothing else is added for decoration.

#### Two greens, and only one of them is for text

`primary` (`#1d8049`) is the green that fills a button and sets a word of text.
White on it is 5.0:1.

`brand-mint` (`#2fb36b`) is the logo's green and is **decorative only**, at
2.6:1. It draws the passed segments of the progress bar and the check on a
passed step, where nothing has to be read. It is never used for text under 24px,
and never as a fill behind text. The hat's yellow (`#fbbf24`) follows the same
rule and is rarer still. Reaching for either on a label is the one way to make
this palette fail a contrast check, so the rule is absolute rather than a
judgement call.

#### The soft treatments

Failure uses a soft treatment rather than shadcn's solid destructive:
`#fef2f2` background, `#fecaca` border, `#b91c1c` text. Solid red reads as
punitive on a screen where a student has just been told they fell short. These
three are unchanged by the brand; the soft palette around them already softens
how they read.

Success badges mirror it: `#e6f7ed`, `#b6e5c8`, `#19713f`.

Caution is the same shape again, in the hat's yellow family: `#fff6d1`,
`#fde68a`, `#8a5a00`. It carries the upload warning, the late clock and the PDF
notice.

The success three are also a **button** treatment, the accent's version of the
soft-red one. An icon button that creates something (new class, upload a
reading) uses it, so it sits beside the pencil and the bin as one set of quiet
controls rather than a solid green block among outlines. Solid green stays for
the button that finishes a form: Create class, Save reading, Next.

#### Surfaces

White is a surface, not the page. Anything that should lift off the mint says so
with `bg-card`: cards, dialogs, popovers and dropdowns, inputs and textareas,
tables, the tutoring chat's composer, and the reading pane. The reading pane
stays white deliberately — it is a long read, and the colour belongs around it
rather than under it. A dashed empty state is left on the page's own colour,
since it is a placeholder for a surface rather than one itself.

#### The logo

The logo files are in `frontend/public/brand/`, and `components/Logo.tsx`
renders them. `sensee-i-logo.svg` is the default; `sensee-i-logo-white.svg` is
for a dark or coloured ground, with `-on-light` and `-on-green` lock-ups beside
them. All carry their own outlined type, so the logo's font (Fredoka) is never
loaded — interface text stays in Nunito. The same folder holds the favicon, the
app icons and the sensei on his own.

### Type

Nunito, weights 400, 600 and 700. Its rounded terminals answer the Fredoka in
the logo, which a grotesque did not. Nunito also runs lighter than Geist did at
the same number, so each weight in the ramp moved up one step: what the design
system calls medium is 600 and semibold is 700. That mapping lives once in
`tailwind.config.js` under `fontWeight`, so `font-medium` and `font-semibold`
mean the new numbers everywhere without a single class changing.

| Role | Size | Weight | Tracking |
| --- | --- | --- | --- |
| Page title | 24px | 700 | -0.02em |
| Section or card title | 14px | 600 | |
| Body and UI | 14px | 400 | |
| Secondary and metadata | 13px | 400 | |
| Smallest label | 12px | 400 or 600 | |

The ramp is deliberately moderate, roughly 1.8x from largest to smallest.
Hierarchy comes from weight and colour rather than size. An earlier draft ran 62px
against 11px and read as a marketing page.

Reading content sits at 15px with 1.75 line height, the only place body type goes
above 14px.

`font-mono` is untouched by this and stays the system monospace stack. Join
codes, participant IDs and the chatbot's code blocks are read character by
character, where 0 against O and 1 against l have to stay apart.

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

Stroke colour is `#56665d` for icons beside muted text and `#83938a` for
decorative chevrons.

### Shell

A single top bar, 56px, with a `#d4ebdd` bottom border. No sidebar. There are few
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
- **Student messages** are a right-aligned bubble in the success tint `#e6f7ed`
  with `#3a4740` text. This is the one place the success green carries a meaning
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
