# PocketTally Backend

FastAPI backend managed by `uv` and pinned to Python 3.14.

## Start

```bash
uv sync
uv run pocket-tally-backend
```

API documentation is available at <http://127.0.0.1:8000/docs>, and the health
endpoint is `GET /api/v1/health`.

Copy `.env.example` to `.env` to override configuration. All environment
variables use the `POCKET_TALLY_` prefix.

## Test

```bash
uv run pytest
```

Long-lived services are initialized in `lifespan.py` and stored in
`app.state.resources`. Route handlers access them through the typed aliases in
`dependencies.py`, such as `ResourcesDep` and `RequestContextDep`.
