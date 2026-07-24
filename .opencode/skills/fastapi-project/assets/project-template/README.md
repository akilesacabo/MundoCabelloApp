# FastAPI project scaffold

A domain-driven FastAPI skeleton following the conventions in the `fastapi-project` skill:
async-first, Pydantic v2, SQLAlchemy 2.0 async, the `Annotated` dependency style, `lifespan`,
centralized error handling, pagination, and Alembic.

## Layout
- `src/config.py` — typed settings (pydantic-settings)
- `src/database.py` — async engine + `get_db` dependency
- `src/models.py` — SQLAlchemy `Base` with a naming convention
- `src/main.py` — app, lifespan, CORS, exception handler, health checks, router includes
- `src/items/` — example domain (router / schemas / models / service / dependencies / exceptions)
- `tests/` — async test client + a sample test
- `alembic/` — async-aware migrations

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env          # edit DATABASE_URL
# start Postgres, then:
alembic revision --autogenerate -m "init"
alembic upgrade head
uvicorn src.main:app --reload
```
Docs at http://localhost:8000/docs (shown only when ENVIRONMENT is local/staging).

## Test / lint
```bash
pytest
ruff check --fix src tests && ruff format src tests
```

## Make it yours
Replace the example `items/` domain with your real domains. Each new domain gets its own module with
the same file shape; keep business logic in `service.py` and HTTP wiring in `router.py`.
