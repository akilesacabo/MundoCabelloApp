# Architecture: structure, async, and dependencies

In-depth reference. Read this when laying out a project, deciding sync vs async, or designing the
dependency graph.

## Contents
- [Full project structure](#full-project-structure)
- [Why domain-driven beats type-driven](#why-domain-driven-beats-type-driven)
- [Async deep dive](#async-deep-dive)
- [Dependency injection patterns](#dependency-injection-patterns)
- [REST consistency for reusable dependencies](#rest-consistency-for-reusable-dependencies)

---

## Full project structure

```
fastapi-project/
├── alembic/                  # database migrations
├── src/
│   ├── config.py             # global settings (pydantic-settings)
│   ├── database.py           # engine, async_sessionmaker, get_db
│   ├── models.py             # SQLAlchemy declarative Base + naming convention
│   ├── schemas.py            # global Pydantic base models
│   ├── exceptions.py         # global custom exceptions
│   ├── pagination.py         # shared pagination params/response
│   ├── main.py               # FastAPI(), lifespan, middleware, CORS, handlers
│   │
│   ├── auth/                 # DOMAIN
│   │   ├── router.py         # APIRouter — HTTP wiring only
│   │   ├── schemas.py        # request/response Pydantic models
│   │   ├── models.py         # SQLAlchemy tables
│   │   ├── dependencies.py   # e.g. get_current_user, valid_token
│   │   ├── constants.py      # error codes, enums, static values
│   │   ├── exceptions.py     # InvalidCredentials, etc.
│   │   ├── service.py        # business logic + DB access
│   │   └── utils.py          # pure, stateless helpers
│   ├── posts/                # DOMAIN (same shape)
│   └── external/             # third-party clients (s3, stripe, ...)
│       ├── s3.py
│       └── stripe.py
├── tests/
│   ├── conftest.py           # global fixtures + async client
│   ├── auth/
│   └── posts/
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── .env                      # never committed
├── .env.example              # committed, documents required vars
├── alembic.ini
├── pyproject.toml            # ruff config, project metadata
└── Dockerfile                # multi-stage
```

A domain module only needs the files it actually uses — a read-only domain may have no `service.py`
mutations and no `constants.py`. Don't create empty files for symmetry.

## Why domain-driven beats type-driven

Type-driven layout (`src/routers/`, `src/models/`, `src/schemas/`) means a single feature is smeared
across the whole tree; touching one feature forces edits in four distant folders, and unrelated
features collide in the same files. Domain-driven layout keeps everything for a feature together, so
modules stay cohesive and can even be extracted into separate services later with little churn.

Use **absolute imports** (`from src.auth import service as auth_service`). Relative imports
(`from . import service`) get fragile the moment you move a module and make cross-domain references
ambiguous.

## Async deep dive

FastAPI is async-first but allows sync routes. The failure mode that takes down production is mixing
them incorrectly.

```python
import asyncio, time
from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

router = APIRouter()

# ❌ DISASTER: blocks the whole event loop. Every other request stalls for 10s.
@router.get("/terrible")
async def terrible():
    time.sleep(10)
    return {"ok": True}

# ✅ ACCEPTABLE: a plain `def` route runs in a threadpool, so only one thread is tied up.
@router.get("/acceptable")
def acceptable():
    time.sleep(10)
    return {"ok": True}

# 🚀 IDEAL: truly non-blocking async I/O.
@router.get("/ideal")
async def ideal():
    await asyncio.sleep(10)
    return {"ok": True}

# 🔧 BRIDGE: call a sync SDK from an async route without blocking the loop.
@router.get("/bridge")
async def bridge():
    result = await run_in_threadpool(heavy_sync_call, arg)
    return {"result": result}
```

Decision guide:

- **Awaitable I/O** (async DB driver, `httpx.AsyncClient`, async Redis) → `async def`.
- **Blocking I/O you cannot await** (a legacy sync client) → either a plain `def` route, or
  `run_in_threadpool` from inside an `async def`.
- **CPU-bound** (encode video, hash millions of values, crunch big DataFrames) → the GIL means threads
  give no parallelism; offload to Celery/Arq/RQ or `multiprocessing`/a separate service.

**Dependencies follow the same rule.** A sync dependency is dispatched to the threadpool too, which is
wasteful for small non-I/O work — prefer `async def` dependencies unless you specifically need a
thread.

Quick audit grep when reviewing code: look for `time.sleep`, `requests.`, `httpx.Client(` (the sync
client), or a sync `Session`/`create_engine` used inside any `async def`.

## Dependency injection patterns

### Beyond injection: validate and authorize

Dependencies are the idiomatic place to validate that a resource exists and that the caller may act on
it. A dependency that raises stops the request before the route body runs.

```python
from typing import Annotated
from fastapi import Depends
from pydantic import UUID4

async def valid_post_id(post_id: UUID4) -> Post:
    post = await service.get_by_id(post_id)
    if not post:
        raise PostNotFound()
    return post

@router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(post: Annotated[Post, Depends(valid_post_id)]):
    return post  # guaranteed to exist
```

### Chaining + per-request caching

FastAPI caches each dependency's result **within a single request scope**. So if `parse_jwt_data` is
required by `valid_owned_post`, `valid_active_creator`, and the route itself, it runs **once** and the
result is shared. This lets you decompose into many small, single-purpose dependencies without paying
to recompute them.

```python
async def parse_jwt_data(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except InvalidTokenError:
        raise InvalidCredentials()
    return {"user_id": payload["id"]}

async def valid_owned_post(
    post: Annotated[Post, Depends(valid_post_id)],
    token_data: Annotated[dict, Depends(parse_jwt_data)],
) -> Post:
    if post.creator_id != token_data["user_id"]:
        raise NotOwner()
    return post

async def valid_active_creator(
    token_data: Annotated[dict, Depends(parse_jwt_data)],
) -> User:
    user = await users_service.get_by_id(token_data["user_id"])
    if not user.is_active:
        raise UserIsBanned()
    if not user.is_creator:
        raise UserNotCreator()
    return user
```

### Reusable typed aliases

Define `Annotated` aliases once and reuse them everywhere — this is the cleanest modern style:

```python
# src/dependencies.py
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]

# usage
@router.get("/items")
async def list_items(db: DbSession):
    ...
```

## REST consistency for reusable dependencies

Designing RESTful resource paths makes dependency reuse natural across routes like
`GET /courses/{course_id}`, `GET /courses/{course_id}/chapters/{chapter_id}/lessons`, and
`GET /chapters/{chapter_id}`.

The one caveat: **use the same path-variable name** wherever it refers to the same entity. If both
`GET /profiles/{profile_id}` and `GET /creators/{creator_id}` validate that a profile exists (and the
second also checks it's a creator), rename the second to `GET /creators/{profile_id}` so you can chain
`valid_profile_id` → `valid_creator_id`:

```python
# profiles/dependencies.py
async def valid_profile_id(profile_id: UUID4) -> Profile:
    profile = await service.get_by_id(profile_id)
    if not profile:
        raise ProfileNotFound()
    return profile

# creators/dependencies.py
async def valid_creator_id(
    profile: Annotated[Profile, Depends(valid_profile_id)],
) -> Profile:
    if not profile.is_creator:
        raise ProfileNotCreator()
    return profile
```
