---
name: fastapi-project
description: >-
  Build and review production-grade FastAPI projects, APIs, backends, and microservices in Python
  using battle-tested conventions: domain-driven structure, async correctness, Pydantic v2 validation,
  SQLAlchemy 2.0, dependency injection, Alembic migrations, testing, and deployment. Use this skill
  whenever the user wants to create, scaffold, structure, refactor, or review a FastAPI app, REST API,
  or web service — or asks about FastAPI project layout, async vs sync routes, Pydantic models,
  organizing routers/services/dependencies, database access, or production deployment — EVEN IF they
  don't literally say "best practices". If a task involves FastAPI and goes beyond a one-line snippet,
  consult this skill first.
---

# FastAPI Project

A workflow and a set of conventions for building FastAPI applications that stay fast, correct, and
maintainable as they grow. The conventions are adapted from the widely-used
`zhanymkanov/fastapi-best-practices` repository, corrected and extended with current (2025–2026)
recommendations (notably the `Annotated[...]` dependency style, async-aware deployment, pagination,
N+1 avoidance, and centralized error handling).

## How to use this skill

1. **Identify the task type** and follow the matching workflow below.
2. **Apply the Core Conventions** (this file) — they cover ~80% of decisions.
3. **Read the relevant `references/` file** when you need depth on a specific area. Do not read all
   of them up front; pull in only what the task needs.
4. **Reuse the scaffold** in `assets/project-template/` when creating a new project — copy it and
   adapt rather than writing boilerplate from memory.

### Reference map (read on demand)

| Need… | Read |
|---|---|
| Folder structure, async rules, dependency injection, REST consistency | `references/architecture.md` |
| Pydantic v2 schemas, SQLAlchemy 2.0 async, repositories vs services, Alembic | `references/data-layer.md` |
| Deployment, workers, security, testing, observability, exception handling | `references/production.md` |

---

## Workflows

### A. Create a new FastAPI project / scaffold

1. Briefly confirm: database (Postgres assumed by default), sync vs async DB driver (default async),
   and whether they want auth scaffolding. If the user has already specified these, don't re-ask.
2. Copy `assets/project-template/` into the target location and rename the placeholder domain
   (`items/`) to the user's first real domain if known.
3. Wire up: `src/config.py` settings, `src/database.py` session, `src/main.py` lifespan + router
   includes + CORS + exception handlers.
4. Show the resulting tree and a `make run` / `uvicorn` command to start it.
5. Mention the next steps the scaffold leaves stubbed (Alembic init, first migration, `.env`).

### B. Add a feature / domain to an existing project

1. Detect the existing structure first (domain-driven vs type-driven) and **match it** — don't impose
   a different layout on an existing codebase.
2. For a new domain, create the standard module files (`router.py`, `schemas.py`, `models.py`,
   `service.py`, `dependencies.py`, `exceptions.py`, `constants.py`) — only the ones the feature
   actually needs.
3. Keep business logic in `service.py`, validation/authorization in `dependencies.py`, HTTP wiring in
   `router.py`. The router must not contain DB queries or business rules.

### C. Review / refactor / debug existing FastAPI code

Run through this checklist and report findings (most impactful first):

- **Blocking the event loop**: any `time.sleep`, sync `requests`/`httpx.Client`, or sync DB driver
  inside an `async def` route or dependency. This is the #1 production killer. (See architecture.md.)
- **Logic in routers**: DB queries or business rules living in the route function instead of a service.
- **Missing validation**: raw `dict`/`str` where a Pydantic model with constraints belongs.
- **N+1 queries**: ORM relationships accessed in a loop without `selectinload`/`joinedload`.
- **Unbounded queries**: list endpoints without pagination or a `limit`.
- **Old dependency style**: `param: X = Depends(...)` instead of `param: Annotated[X, Depends(...)]`.
- **Deprecated lifecycle**: `@app.on_event("startup")` instead of a `lifespan` context manager.
- **Secrets via `os.getenv`** scattered around instead of a single typed `Settings`.
- **`BackgroundTasks` for critical work** that must not be silently lost (payments, invoices).

---

## Core Conventions

### 1. Structure: group by domain, not by file type

Scale by feature module, inspired by Netflix Dispatch — not by global `routers/`, `models/`,
`schemas/` folders, which couple everything and scale badly.

```
src/
├── config.py          # global settings (pydantic-settings BaseSettings)
├── database.py        # engine, session factory, get_db dependency
├── models.py          # SQLAlchemy declarative Base (+ naming convention)
├── exceptions.py      # global custom exceptions
├── pagination.py      # shared pagination params/response
├── main.py            # FastAPI() app, lifespan, CORS, exception handlers
└── <domain>/          # e.g. auth/, posts/, payments/
    ├── router.py      # APIRouter — HTTP wiring ONLY
    ├── schemas.py     # Pydantic request/response models
    ├── models.py      # SQLAlchemy tables for this domain
    ├── service.py     # business logic + DB access lives here
    ├── dependencies.py# validation/authorization (e.g. valid_post_id)
    ├── exceptions.py  # domain-specific exceptions
    ├── constants.py   # error codes, enums, static values
    └── utils.py       # pure, stateless helpers
```

Rules: the **router never holds business logic or DB queries**. Use **absolute imports**
(`from src.auth import service`), not relative ones. Full tree and rationale: `references/architecture.md`.

### 2. Async correctness (the rule that prevents outages)

- `async def` routes run **on the event loop**. Anything blocking inside them freezes the **entire
  server** for all users. Never put `time.sleep`, sync `requests`, or a sync DB driver in an
  `async def`.
- `def` (sync) routes run **in a threadpool**, so blocking there only ties up one thread. Use a plain
  `def` route when you must call blocking code and can't await it.
- To call a sync SDK from an async route, wrap it: `await run_in_threadpool(client.do_thing, arg)`
  (from `fastapi.concurrency`).
- CPU-bound work (image/video, heavy crypto, big pandas) is blocked by the GIL — neither async nor the
  threadpool helps. Offload to a real task queue (Celery / Arq / RQ) or a separate process.
- **Prefer `async` dependencies too** — sync dependencies also run in the threadpool and add overhead.

Concise reference table:

| Route / dep does… | Use | Why |
|---|---|---|
| Awaitable I/O (async DB, `httpx.AsyncClient`) | `async def` | Non-blocking, ideal |
| Blocking I/O you can't await | `def` | Runs in threadpool, doesn't block loop |
| Sync SDK from inside async | `await run_in_threadpool(...)` | Lets the loop breathe |
| CPU-heavy work | task queue / subprocess | GIL makes threads useless here |

### 3. Validate aggressively with Pydantic v2

Push constraints into schemas so bad data never reaches your logic. Use `Field(min_length=…, ge=…,
pattern=…)`, `EmailStr`, `AnyUrl`, and `StrEnum` (Py 3.11+). Raising a `ValueError` inside a
`@field_validator` automatically becomes a clean **422** response. Define a shared base model for
common config (`from_attributes=True`, UTC datetime serialization). Details + the verified custom base
model: `references/data-layer.md`.

Modern dependency style — **always prefer `Annotated`**:

```python
from typing import Annotated
from fastapi import Depends

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

@router.get("/me")
async def read_me(user: CurrentUser) -> UserResponse:
    return user
```

This is cleaner than `user: User = Depends(get_current_user)`, lets you alias and reuse dependency
types, and keeps non-default args from fighting default ones.

### 4. Dependencies: chain, reuse, and validate with them

Dependencies aren't only for injection — use them to validate resources and authorize requests, then
chain small ones into bigger ones. FastAPI **caches a dependency's result within a single request**,
so a shared dependency (e.g. `parse_jwt_data`) called by three others runs only once.

```python
async def valid_post_id(post_id: UUID4) -> Post:
    post = await service.get_by_id(post_id)
    if not post:
        raise PostNotFound()        # -> 404 via an exception handler
    return post

async def valid_owned_post(
    post: Annotated[Post, Depends(valid_post_id)],
    user: Annotated[User, Depends(get_current_user)],
) -> Post:
    if post.creator_id != user.id:
        raise NotOwner()            # -> 403
    return post
```

Keep **path variable names consistent across endpoints** (always `profile_id`, even on a
`/creators/{profile_id}` route) so dependencies are reusable. More: `references/architecture.md`.

### 5. Database & data flow: SQL-first

Let the database do the heavy lifting — joins, aggregation, and even building nested JSON are far
faster in Postgres than pulling thousands of rows into Python loops. Use SQLAlchemy 2.0's async API
(`AsyncSession`, `async_sessionmaker`). Naming conventions: `snake_case`, **singular** table names,
module prefixes (`payment_account`, `post_like`), `_at` for datetimes, `_date` for dates, and concrete
FK names (`creator_id`, not bare `id`). Repository-vs-service, eager loading to kill N+1, and Alembic
setup: `references/data-layer.md`.

### 6. Lifecycle, config, and production

- Use a **`lifespan`** async context manager for startup/shutdown (open DB pools, Redis, ML models).
  `@app.on_event` is deprecated.
- Centralize all config in one typed `Settings(BaseSettings)` from **pydantic-settings**; never sprinkle
  `os.getenv` calls.
- Map domain exceptions to HTTP responses with **`@app.exception_handler`** so routes can just `raise`
  semantic errors.
- Deployment: see `references/production.md` — and note the corrected worker guidance there (the common
  `(2 × cores) + 1` formula is for **sync** workers; async event-loop workers usually want roughly
  **one worker per core**, or one worker per container scaled horizontally).

### 7. Test async from day zero

Use `httpx.AsyncClient` with `ASGITransport` (not the old `TestClient` for async DB code, and not the
unmaintained `async_asgi_testclient`). Swap auth and external clients via `app.dependency_overrides`
instead of monkeypatching. Full fixtures: `references/production.md`.

---

## Output expectations

- When generating files, follow the domain structure above and put each concern in its proper module.
- Default to the `Annotated` dependency style, `lifespan`, async SQLAlchemy, and pydantic-settings.
- Prefer creating real files (the scaffold) over pasting one giant code block when the user is starting
  or extending a project.
- Call out any place where a choice is a genuine tradeoff (e.g. repository pattern vs plain service
  functions) rather than presenting one option as the only correct answer.
