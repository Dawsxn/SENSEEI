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

## Environments

Three branches, two environments. A branch is a version of the code; an
environment is somewhere it runs. They are not the same thing, and every branch
can be run locally.

| | Local | Development | Production |
| --- | --- | --- | --- |
| Runs from | Any branch you check out | `develop` | `main` |
| Where | `localhost:5173` | `senseei-dev.<host>` | `senseei.<host>` |
| Database | Docker Postgres, one per developer | `senseei-dev` | `senseei-prod` |
| Data | Seeded synthetic | Seeded synthetic, reset freely | Real |
| LLM provider | `mock` by default | `mock` | Real provider |
| Deploys | Never | On merge to `develop` | On merge to `main` |
| Migrations | Run by hand | On deploy | On deploy |
| Instance tier | n/a | Free, sleeping is fine | Paid, must not sleep |

**One database per environment, never shared.** This is the rule the rest of the
structure exists to enforce. A migration run against development must not be able
to reach production data.

**Data never flows down from production.** If development needs realistic data,
seed it. Production holds student session transcripts.

**Three sets of secrets, no overlap.** Database URL, Google client ID and secret,
LLM API key. A leaked development key must not open production.

**Use the `mock` provider everywhere except production.** Every environment that
runs the tutoring loop against a real model costs tokens, and a development
environment left running is a bill for nothing. Switch to the real provider
deliberately, when testing agent behaviour specifically.

**Development can sleep, production cannot.** A cold start in development costs
fifteen seconds of your own time. A cold start in production happens partway
through somebody's session.

### Deliberately not doing

**Preview environments per pull request.** Google does not permit wildcards in
OAuth redirect URIs and preview URLs are generated per PR, so sign-in would break
on every preview unless each URL were registered by hand.

**A separate staging tier.** Development doubles as it. Add a third environment
when there is a release worth rehearsing somewhere that is not the environment
people are using.

### Seeding

A student sees nothing until an instructor has created a class and uploaded a
reading with core components. Every fresh database is unusable until that exists,
so the seed script is not a convenience and should be written alongside the
schema rather than after it becomes annoying.

### Migrations

Alembic runs automatically on deploy, in the same order everywhere, so
development rehearses exactly what production will do.

Two branches that each add a migration will produce two revision heads, and
Alembic refuses to run until they are reconciled. Say when you are adding one.

## Deployment

Render or Railway for the FastAPI service plus managed PostgreSQL, in a Singapore
region for latency from Manila. Decide between the two when it comes time.

**Serve the built SPA as static files from FastAPI** rather than deploying it
separately:

```
npm run build      ->  dist/
FastAPI  /api/*    ->  the API
         /*        ->  dist/, falling back to index.html
```

One service, one deploy, one origin, no CORS. The cost is that a frontend-only
change redeploys everything, which does not matter at this size.

Register a Google OAuth redirect URI for each environment, including
`http://localhost:5173`, or sign-in will not work outside production.

The manuscript never mentions deployment, so none of this contradicts it.

## Related

- `docs/context/design-system.md`, tokens and component conventions
- `docs/context/data-model.md`, what PostgreSQL holds
- `docs/context/agent-contracts.md`, the provider layer and its configuration
- `docs/context/student-tutoring-loop.md`, the behaviour the frontend implements
