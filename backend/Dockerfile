# syntax=docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.14-slim-bookworm
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.9.18

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS builder
COPY --from=uv /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_HTTP_TIMEOUT=120 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY app ./app
RUN uv sync --frozen --no-dev --no-editable

FROM ${PYTHON_IMAGE} AS runtime

ARG APP_VERSION=0.1.0
ARG VCS_REF=local
LABEL org.opencontainers.image.title="PocketTally Backend" \
      org.opencontainers.image.description="PocketTally FastAPI backend" \
      org.opencontainers.image.source="https://github.com/LouisLiuNova/PocketTally" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.licenses="MIT"

ENV PATH="/app/.venv/bin:${PATH}" \
    HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POCKET_TALLY_ENVIRONMENT=production \
    POCKET_TALLY_DEBUG=false \
    POCKET_TALLY_HOST=0.0.0.0 \
    POCKET_TALLY_PORT=8000 \
    POCKET_TALLY_LOG_JSON=true \
    POCKET_TALLY_DATABASE_PATH=/data/pocket-tally.sqlite3 \
    POCKET_TALLY_BACKUP_DIRECTORY=/backups

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
RUN mkdir -p /data /backups && chown -R 10001:10001 /data /backups

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD ["python", "-c", "import json,urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)); raise SystemExit(0 if data.get('ready') else 1)"]

CMD ["pocket-tally-backend"]
