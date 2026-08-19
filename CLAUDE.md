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

- `agents/` — the shared agent package: the Assessment Agent (`assessment.py`),
  the rubric loader (`rubric.py`), the swappable LLM `providers/`, and the
  versioned `prompts/` and `rubrics/`. Installed via the root `pyproject.toml`
  (`pip install -e ".[gemini]"`), so the eval harness and the future FastAPI
  backend import the *same* code — the eval must never validate a separate
  implementation from the one that ships. The Tutor Agent will join it here.
- `assessment-agent-eval/` — the standalone Assessment Agent evaluation harness
  (labeled dataset, eval runner, comparison + reporting). Measures the agent in
  `agents/`; does not contain it. Has its own README and CHANGELOG.
- `docs/thesis/` — thesis artifacts: diagrams and presentation decks. Not code.

## Skills

Two repo skills are available to anyone running Claude Code here:

- `/start-branch` — create a correctly named branch off an up-to-date `develop`
- `/create-pr` — open a PR from the current branch following the conventions
