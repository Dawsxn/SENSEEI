# SENSEE-I

An LLM-based Intelligent Tutoring System that helps students build conceptual
understanding of expository texts using the SEE-I framework (State, Elaborate,
Exemplify, Illustrate). Undergraduate thesis, DLSU Software Technology.

## Architecture at a glance

Four layers, frontend to back:

- **Frontend** — React SPA, split into a Student UI (reading list, tutoring loop)
  and an Instructor UI (upload, classes, dashboard)
- **API layer** — FastAPI, grouped into a Reading & Class API, a Session API, and
  an Analytics API
- **Core** — an Orchestrator (plain backend logic: pass/fail, retries, step
  advancement) that drives two LLM-backed agents, the Tutor Agent and the
  Assessment Agent
- **External** — PostgreSQL, and an LLM provider (not yet chosen)

Only the two agents call an LLM. The Orchestrator is fixed-rule code, not a
third agent.

## Conventions — always apply

@docs/conventions/git-workflow.md
@docs/conventions/pull-requests.md

## Reference — open when relevant

- `agents/` — the shared agent package: both agents (`assessment.py` grades a
  response, `tutor.py` writes what the student reads), the rubric loader
  (`rubric.py`), shared provider backoff (`retry.py`), the swappable LLM
  `providers/`, and the versioned `prompts/` and `rubrics/`. Installed via the root `pyproject.toml`
  (`pip install -e ".[gemini]"`), so the eval harness and the future FastAPI
  backend import the *same* code — the eval must never validate a separate
  implementation from the one that ships.
- `assessment-agent-eval/` — the standalone Assessment Agent evaluation harness
  (labeled dataset, eval runner, comparison + reporting). Measures the agent in
  `agents/`; does not contain it. Has its own README and CHANGELOG.
- `docs/context/` holds the design context for the app itself:
  `student-tutoring-loop.md` (session state machine, dialogue moves, fallback),
  `agent-contracts.md` (what each agent receives and returns),
  `data-model.md` (entities, relationships, retention), `tech-stack.md`
  (libraries, auth, deployment), and `design-system.md` (tokens, type scale,
  component conventions). Open these before writing app code. They record
  decisions that are not derivable from the codebase.
- `backend/` — the FastAPI app: `settings.py` (environment config), `db.py`
  (async engine and the per-request session), `main.py` (the app), `models/`
  (the SQLModel schema from `docs/context/data-model.md`, no ORM relationships —
  under async, lazy loads raise, so queries use explicit joins), `orchestrator.py`
  (the fixed-rule loop: pass/fail, retries, step advancement — pure, no LLM and no
  database), `services/` (the imperative shell that carries a decision out, over
  Server-Sent Events), `routers/` (the HTTP endpoints), and `deps.py` (a stubbed
  student identity until `feat/auth`, and the agent pair). Imports the agents
  rather than reimplementing them. Run it with `uvicorn backend.main:app --reload`,
  after `docker compose up -d --wait`.
- `migrations/` — Alembic, reading its URL from `backend.settings`. Bring a
  local database up to date with `alembic upgrade head`. `scripts/seed.py` then
  fills it with development data (one instructor, two classes, five students,
  three readings, some with real sessions), sourced from the eval dataset so the
  app and the eval study the same material.
- `scripts/session.py` — plays one tutoring session in the terminal, so the
  agents can be exercised without a database, server or UI. `--offline` stubs
  both and costs nothing. It has its own inline copy of the loop for the terminal;
  the backend's authoritative loop is `backend/orchestrator.py`, and both now
  share the attempt limit from there.
- `docs/thesis/` — thesis artifacts: diagrams and presentation decks. Not code.

## Skills

Two repo skills are available to anyone running Claude Code here:

- `/start-branch` — create a correctly named branch off an up-to-date `develop`
- `/create-pr` — open a PR from the current branch following the conventions
