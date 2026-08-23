# Tech stack

What the app is built with.

The manuscript fixes the four architecture components (§4.4.1, Table 4.6) but
nothing below them. Everything at library level was decided during development
and is recorded here because it is not derivable from the repo yet.

## Frontend

| Choice | Notes |
| --- | --- |
| React, single page app | From Table 4.6 |
| Vite | Build tool |
| Tailwind CSS | |
| shadcn/ui | Components are copied into the repo rather than imported, so they are ours to edit |
| Geist | Typeface, via Google Fonts. Not Inter |
| TanStack Query | Server state. The tutoring loop is request-response, which is what it is for |
| Recharts | Instructor dashboard charts. shadcn's chart components wrap it |

**No client state library.** React state plus TanStack Query's cache covers what
this app does. Add one only when something concrete forces it.

shadcn was chosen over Mantine and MUI because the two signature screens, the
split-screen tutoring view and the chat, are custom regardless of library, and
because owning the component source suits agent-assisted development. MUI and Ant
Design were rejected for carrying a visual identity that takes real work to shed.

Visual tokens, type scale, and component conventions live in
`design-system.md`.

## Backend

| Choice | Notes |
| --- | --- |
| Python, FastAPI | From Table 4.6 |
| PostgreSQL | From Table 4.6 |
| SQLModel | Models are Pydantic models, so one definition serves both database and API |
| Alembic | Migrations |
| pydantic-settings | Configuration, read from environment variables at startup |

SQLModel rather than Prisma: Prisma is a Node and TypeScript ORM, and using it
from Python means a third-party community client that lags upstream and has had
intermittent maintenance. SQLModel is written by FastAPI's author, sits on
SQLAlchemy, and keeps the declarative typed-model feel without leaving the
ecosystem.

## Authentication

Google OAuth, restricted to DLSU addresses. A non-DLSU Google account cannot sign
in at all, so enrolment is not the only gate. See `data-model.md`.

## LLM provider

The provider layer lives in `agents/providers/`, shared between the eval harness
and the backend. Settings reach it through `pydantic-settings`, never from the
eval's `config.yaml`, which configures eval runs only. See `agent-contracts.md`.

The model itself is still open. Preliminary results used Gemini 3.1 Pro at a low
thinking level, which the manuscript notes is not necessarily what ships.

## Testing

| Layer | Tool |
| --- | --- |
| Backend | pytest, already used by the eval harness |
| Frontend | Vitest with React Testing Library, comes with Vite |
| End to end | None |

End-to-end tests are deliberately skipped. Playwright is real work and a thesis
timeline spends it better elsewhere.

The one place tests are not optional is the **Orchestrator**. Attempt counting and
step advancement fail silently and corrupt the data they produce, which is the
worst possible failure mode for a study whose results depend on that data.

## Deployment

Render or Railway for the FastAPI service plus managed PostgreSQL, in a Singapore
region for latency from Manila. Decide between the two when it comes time.

Two constraints:

1. **Do not run data collection on a free tier.** Free instances sleep, and a
   cold start mid-session costs a participant.
2. **Serve the built SPA as static files from FastAPI** rather than deploying it
   separately. That removes CORS and leaves one thing to deploy.

The manuscript never mentions deployment, so none of this contradicts it.

## Related

- `docs/context/design-system.md`, tokens and component conventions
- `docs/context/data-model.md`, what PostgreSQL holds
- `docs/context/agent-contracts.md`, the provider layer and its configuration
- `docs/context/student-tutoring-loop.md`, the behaviour the frontend implements
