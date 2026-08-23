# Tech stack

What the app is built with, and what is still open.

The manuscript fixes the four components (§4.4.1, Table 4.6) but nothing below
them. Everything at library level was decided during development and is recorded
here because it is not derivable from the repo yet.

## Decided

### Frontend

| Choice | Notes |
| --- | --- |
| React, single page app | From Table 4.6 |
| Tailwind CSS | |
| shadcn/ui | Components are copied into the repo rather than imported, so they are ours to edit |
| Geist | Typeface, via Google Fonts. Not Inter |

shadcn was chosen over Mantine and MUI because the two signature screens, the
split-screen tutoring view and the chat, are custom regardless of library, and
because owning the component source suits agent-assisted development. MUI and Ant
Design were rejected for carrying a visual identity that takes real work to shed.

### Backend

| Choice | Notes |
| --- | --- |
| Python, FastAPI | From Table 4.6 |
| PostgreSQL | From Table 4.6 |

### Authentication

Google OAuth, restricted to DLSU addresses. A non-DLSU Google account cannot sign
in at all, so enrolment is not the only gate. See `data-model.md`.

### LLM provider

The provider layer lives in `agents/providers/`, shared between the eval harness
and the backend. The model itself is still open, and the eval's `config.yaml`
configures eval runs only. See `agent-contracts.md`.

## Interim visual tokens

Recorded here so they are not lost while the screens are still moving. These move
to `design-system.md` once the design settles, and that file supersedes this
section when it exists.

| Token | Value |
| --- | --- |
| Foreground | `#09090b` |
| Muted foreground | `#71717a` |
| Placeholder | `#a1a1aa` |
| Border | `#e4e4e7` |
| Muted surface | `#f4f4f5` |
| Primary | `#16a34a` |
| Card radius | 8px |
| Control radius | 6px |
| Button height | 36px default, 32px small |
| Raised shadow | `0 1px 2px 0 rgba(0,0,0,0.05)` |

These are shadcn's own defaults apart from the primary, which is green per the
project's accent choice. Type runs 24px semibold for page titles against 14px
body and 13px muted, a deliberately moderate ramp.

Structural decisions made alongside them: a top bar with no sidebar, and the
SEE-I progression rendered as a Tabs row rather than bespoke chrome.

## Open

| # | Question | Recommendation |
| --- | --- | --- |
| 1 | Build tool | Vite. It is what shadcn documents for a React SPA and needs no argument |
| 2 | ORM and migrations | SQLAlchemy with Alembic, unless you want something lighter |
| 3 | Data fetching on the client | TanStack Query. The tutoring loop is request-response with server state, which is what it is for |
| 4 | Client state management | Probably none beyond React state. Reach for a library only if something forces it |
| 5 | Charts for the instructor dashboard | Recharts. Carried in with the shadcn choice rather than decided on its own, so say if you want otherwise |
| 6 | Testing | Open |
| 7 | Deployment target | Open. The manuscript never mentions deployment |
| 8 | How the backend reads provider settings at startup | Environment variables into a settings object. Tracked as open question 1 in `agent-contracts.md` |

Nothing in this list blocks the frontend work.

## Related

- `docs/context/data-model.md`, what PostgreSQL holds
- `docs/context/agent-contracts.md`, the provider layer and its configuration
- `docs/context/student-tutoring-loop.md`, the behaviour the frontend implements
