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
| Recharts | Available for instructor dashboard charts, unused so far: the three statistics are a bar, a ranked list and four numbers, which are plain CSS |

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
| SQLAlchemy async with asyncpg | Endpoints are `async def` all the way down |
| Alembic | Migrations |
| pydantic-settings | Configuration, read from environment variables at startup |

**Async, and the reason is streaming rather than load.** A tutoring turn spends
about eight seconds waiting: four on the Assessment Agent, four on the Tutor. On
concurrency alone sync would be fine, since a class is around thirty students and
FastAPI dispatches `def` handlers to a forty-thread pool. What sync cannot do is
stream the Tutor's reply as it generates, which is how every chat interface
behaves and which turns an eight-second blank wait into four seconds and then
visible progress.

Whether the chat actually streams is still open. Async was chosen so that it can,
because retrofitting it later would mean changing the engine, the session
dependency and every handler at once.

One consequence worth knowing: a blocking call inside an `async def` freezes the
whole process, not one worker. The agents are synchronous, so any call into them
from a handler goes through `run_in_threadpool`.

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
| LLM provider | `mock` by default | Real provider while QA-ing the agents, set in the dashboard | Real provider |
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

**Use the `mock` provider by default, and the real one on purpose.** Every
environment that runs the tutoring loop against a real model costs tokens, and an
environment left running is a bill for nothing. Locally the default is `mock`.
Development runs the real provider while the agents are what is being QA-ed,
which is most of the time it is used; switch it to `mock` in the Render dashboard
to stop spending. `render.yaml` leaves `LLM_PROVIDER` to the dashboard for that
reason: a value written in the file would be restored whenever the file changes,
quietly undoing a switch made mid-QA.

Development spends only what a QA tester spends. A stranger who signs in with a
DLSU account is a student in no class, with no readings and so no session to
start, and uploading needs an instructor.

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

**Render**, for the FastAPI service plus managed PostgreSQL, in its Singapore
region for latency from Manila. Chosen over Railway for a free web tier that suits
a development environment, and for Blueprints: `render.yaml` describes the service
and its database together, so setting the environment up is choosing the
repository rather than configuring each piece by hand.

**Serve the built SPA as static files from FastAPI** rather than deploying it
separately:

```
npm run build      ->  frontend/dist/
FastAPI  API routes   ->  the API
         everything else  ->  dist/, falling back to index.html
```

One service, one deploy, one origin, no CORS. The cost is that a frontend-only
change redeploys everything, which does not matter at this size.

### How it is built

| File | What it does |
| --- | --- |
| `Dockerfile` | Builds the frontend in a Node stage, then installs the app on Python and copies `dist` across. One image |
| `render.yaml` | The development environment: the web service (Docker, free, deploys on every merge to `develop`) and its database |
| `scripts/start.py` | The container's command: migrate, seed if the database is empty, then run uvicorn |
| `backend/frontend.py` | Serves `dist`, with every non-API path falling back to `index.html` |

Migrations run on every start rather than in a pre-deploy step, because the free
tier has no such step. A migration that fails stops the start, so a broken
migration never serves traffic.

The seed runs only when `SEED_IF_EMPTY` is `true` and the database has no users,
which on development means its first start and nothing after. Production never
sets it.

`DATABASE_URL` is taken as the host gives it (`postgres://...`); the settings
switch it to the async driver.

### Setting up the development environment

1. In Render: **New > Blueprint**, pick this repository. Render reads
   `render.yaml` and creates `senseei-dev-db` and `senseei-dev`.
2. It asks for the values marked `sync: false`. `APP_BASE_URL` is the service's
   address, `https://senseei-dev.onrender.com` or whatever Render assigns.
   `QA_EMAILS` is your own DLSU email. `LLM_PROVIDER` is `gemini` to QA the
   agents, with `GEMINI_API_KEY` set, or `mock` to spend nothing. The rest are
   the development Google client.
3. In Google Cloud, add `<APP_BASE_URL>/auth/callback` as an authorized redirect
   URI, and while the consent screen is in Testing, add each tester's email as a
   test user.
4. The first deploy builds, migrates an empty database and seeds it. After that,
   every merge to `develop` deploys again.

### QA on the development environment

The sign-in screen's open picker (`AUTH_DEV_BYPASS`) is off there, since on a
public URL it would let anyone in as anyone. Instead, an email in `QA_EMAILS`
signs in with Google as itself and gets **Switch user** in the account menu,
which acts as any seeded person: the instructor, or any of the students with
their sessions. Anyone else who finds the URL has to get past Google, and gets no
switch. Production ignores `QA_EMAILS` entirely.

Register a Google OAuth redirect URI for each environment, including
`http://localhost:5173`, or sign-in will not work outside production.

The manuscript never mentions deployment, so none of this contradicts it.

## Related

- `docs/context/design-system.md`, tokens and component conventions
- `docs/context/data-model.md`, what PostgreSQL holds
- `docs/context/agent-contracts.md`, the provider layer and its configuration
- `docs/context/student-tutoring-loop.md`, the behaviour the frontend implements

## Deploy checklist

Things that only break once deployed, collected as they are found so the deploy
is a checklist rather than a discovery. Staging comes after the features are
finished, so each of these will be met at once.

- [x] **No page route shares a path with an API route.** Pages and the API share
  one origin, so a page at the same path as an endpoint answers a refresh or a
  bookmark with JSON. It happened with `/classes`; the instructor API moved to
  `/instructor/classes`. The instructor's reading pages are at `/library` for
  the same reason, since `/readings` is the students' API. The fallback in
  `backend/frontend.py` refuses any path under an API prefix, so a mistyped API
  call is a JSON 404 rather than a page of HTML.
- [ ] **The Google OAuth redirect URI** is registered for the deployed origin, not
  only `localhost:5173`.
- [x] **The session cookie** is marked secure over HTTPS. It is, outside
  `local`; uvicorn trusts the host's forwarded headers so the app knows the
  request arrived over HTTPS.
- [x] **The PDF worker** loads from the deployed origin. It is a `.mjs` file,
  which Python does not always know is JavaScript; served as anything else the
  browser refuses to start it, so `backend/frontend.py` registers the type.
- [x] **Every dependency is declared.** The first container build failed on
  `greenlet`, which async SQLAlchemy needs and Windows had installed by chance.
  Build the image before deploying a dependency change: `docker build -t senseei .`
