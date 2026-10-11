# One image, one service: FastAPI serves both the API and the built frontend.
# See docs/context/tech-stack.md, "Deployment".
#
#   docker build -t senseei .
#   docker run -p 8000:8000 -e DATABASE_URL=... senseei
#
# Local development does not use this. It runs uvicorn and Vite directly, with
# only Postgres in Docker (docker-compose.yml).

# --- the frontend, built once and copied across ------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- the app --------------------------------------------------------------------
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# The packages first, so a change to app code does not reinstall dependencies.
COPY pyproject.toml ./
COPY agents ./agents
COPY backend ./backend
# Editable, so `backend` and `agents` resolve to /app rather than to a copy in
# site-packages: the app finds frontend/dist and its prompts relative to itself.
RUN pip install -e ".[backend,gemini]"

COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
# The seed's readings come from the eval dataset, so the app and the eval study
# the same material. Only the data, not the harness.
COPY assessment-agent-eval/data ./assessment-agent-eval/data
COPY --from=web /web/dist ./frontend/dist

EXPOSE 8000
CMD ["python", "scripts/start.py"]
