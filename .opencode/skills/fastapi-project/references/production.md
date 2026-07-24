# Production: deployment, security, testing, observability

Read this for serving the app, hardening it, testing async code, and operating it.

## Contents
- [Lifespan instead of on_event](#lifespan-instead-of-on_event)
- [Typed settings](#typed-settings)
- [Centralized exception handling](#centralized-exception-handling)
- [BackgroundTasks vs a real queue](#backgroundtasks-vs-a-real-queue)
- [Docs exposure](#docs-exposure)
- [CORS](#cors)
- [Deployment and workers (corrected)](#deployment-and-workers-corrected)
- [Health checks](#health-checks)
- [Testing async from day zero](#testing-async-from-day-zero)
- [Observability](#observability)
- [Linting with Ruff](#linting-with-ruff)

---

## Lifespan instead of on_event

`@app.on_event("startup"/"shutdown")` is deprecated. Use a `lifespan` context manager to open and
clean up resources (DB pools, Redis, ML models) deterministically.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import redis.asyncio as redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.from_url(settings.redis_url)   # startup
    yield                                                   # app serves requests here
    await app.state.redis.aclose()                          # shutdown

app = FastAPI(lifespan=lifespan)
```

## Typed settings

One source of truth for configuration. `pydantic-settings` validates types and fails fast on missing
required vars — much safer than scattered `os.getenv` calls.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    secret_key: str
    environment: str = "production"
    sql_echo: bool = False
    cors_origins: list[str] = []

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()
```

## Centralized exception handling

Define semantic exceptions once, map them to HTTP responses once, and let routes simply `raise` them.
This keeps routers clean and responses consistent.

```python
# src/exceptions.py
class AppError(Exception):
    status_code = 500
    detail = "Internal server error"

class NotFound(AppError):
    status_code = 404
    detail = "Resource not found"

class PermissionDenied(AppError):
    status_code = 403
    detail = "Permission denied"

# src/main.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
```

## BackgroundTasks vs a real queue

`BackgroundTasks` runs **after the response, in the same worker process**. If the worker dies, the task
is gone — no retries, no visibility, no scheduling.

| Use `BackgroundTasks` when… | Use Celery / Arq / RQ when… |
|---|---|
| Task is short (< ~1s) | Task takes seconds to minutes |
| Losing it silently is acceptable | You need retries / dead-letter handling |
| In-process (send an email, write a log row) | CPU-heavy or needs a separate worker pool |
| No scheduling / rate limiting needed | You need cron, ETA, or rate limiting |

Rule of thumb: if you'd page someone when the task is silently lost (payments, invoices, report
generation), it does not belong in `BackgroundTasks`.

```python
@router.post("/signup")
async def signup(data: SignupIn, bg: BackgroundTasks):
    user = await service.create_user(data)
    bg.add_task(send_welcome_email, user.email)  # fire-and-forget, OK to lose
    return user
```

## Docs exposure

Unless the API is public, hide the interactive docs by default and enable them only on chosen
environments. Treat this as **defense-in-depth, not security** — real protection is authentication and
network controls. Hiding `/docs` only removes a convenience for an attacker; it does not protect an
unauthenticated endpoint.

```python
SHOW_DOCS_ENVS = {"local", "staging"}
app_configs = {"title": "My API"}
if settings.environment not in SHOW_DOCS_ENVS:
    app_configs["openapi_url"] = None  # disables /docs, /redoc, and the schema

app = FastAPI(**app_configs)
```

Also help the generated docs: set `response_model`, `status_code`, `tags`, `summary`, and use the
route `responses=` attribute to document multiple status codes.

## CORS

Only enable CORS if a browser on another origin calls the API, and never use `allow_origins=["*"]`
together with `allow_credentials=True`.

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,   # explicit list, from settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Deployment and workers (corrected)

There are two common ways to run multiple workers:

1. **Uvicorn directly** (modern, simplest): `uvicorn src.main:app --workers N`. Uvicorn has a built-in
   process manager; for many deployments this is all you need.
2. **Gunicorn as a process manager with the Uvicorn worker class** (mature, more knobs):
   `gunicorn src.main:app -k uvicorn.workers.UvicornWorker -w N -b 0.0.0.0:8000`.

**Picking N — this is where the popular advice is wrong.** The often-quoted `(2 × cores) + 1` formula
is a **Gunicorn rule of thumb for *synchronous* workers**, where each worker handles one request at a
time. FastAPI's Uvicorn workers are **async**: a single worker handles many concurrent requests on one
event loop. So:

- For async workers, start around **one worker per CPU core** (sometimes fewer) and tune from load
  tests. Piling on `(2 × cores) + 1` async workers mostly wastes memory without adding throughput.
- In Kubernetes/containers, the common pattern is **one Uvicorn worker per container** and scaling out
  with replicas behind a load balancer — this gives clean per-pod resource limits and graceful
  rolling restarts. Let the orchestrator do the multiplying.

Put a real ASGI/HTTP layer (Uvicorn) behind a reverse proxy or load balancer (nginx, a cloud LB) for
TLS, timeouts, and buffering. Use a **multi-stage Dockerfile** (build deps in one stage, copy only the
runtime artifacts into a slim final image) — see the scaffold's `Dockerfile`.

## Health checks

Expose lightweight endpoints so orchestrators can probe the app. Keep liveness trivial; make readiness
actually check dependencies (DB, Redis) so traffic isn't routed before they're up.

```python
@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}

@app.get("/ready", tags=["ops"])
async def ready(db: DbSession):
    await db.execute(text("SELECT 1"))
    return {"status": "ready"}
```

## Testing async from day zero

Integration tests against a DB with the wrong client cause event-loop errors later. Use
`httpx.AsyncClient` with `ASGITransport` from the start. Don't use the unmaintained
`async_asgi_testclient`.

```python
# tests/conftest.py
from typing import AsyncGenerator
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

```python
# tests/test_posts.py
import pytest

@pytest.mark.asyncio
async def test_create_post(client):
    resp = await client.post("/posts", json={"title": "hi"})
    assert resp.status_code == 201
```

**Override dependencies instead of monkeypatching internals** — swap auth or external clients for
fakes:

```python
from src.auth.dependencies import parse_jwt_data
from src.main import app

def fake_user():
    return {"user_id": "00000000-0000-0000-0000-000000000001"}

@pytest.fixture(autouse=True)
def _override_auth():
    app.dependency_overrides[parse_jwt_data] = fake_user
    yield
    app.dependency_overrides.clear()
```

(Configure `pytest-asyncio` with `asyncio_mode = "auto"` in `pyproject.toml` to drop the per-test
`@pytest.mark.asyncio` if you prefer.)

## Observability

- **Structured logging** (e.g. `structlog`) — emit JSON logs with a `request_id` so lines correlate
  across a request. Add middleware that generates/propagates a correlation ID header.
- **Metrics** — Prometheus (`prometheus-fastapi-instrumentator`) for request rate, latency, error rate.
- **Tracing** — OpenTelemetry to follow a request across services.
- **Rate limiting** — `slowapi` (or do it at the gateway/proxy) to protect expensive endpoints.

These are pointers; wire them in as the project's scale warrants rather than all at once on day one.

## Linting with Ruff

Use **Ruff** (Rust-based) — it replaces flake8, isort, autoflake, and **black** (Ruff has its own
formatter), running hundreds of rules in milliseconds. A simple script or a pre-commit hook keeps the
whole team consistent:

```sh
#!/bin/sh -e
ruff check --fix src
ruff format src
```
