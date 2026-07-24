# Data layer: Pydantic v2, SQLAlchemy 2.0, Alembic

Read this for schema design, the database access layer, avoiding N+1 queries, pagination, and
migrations.

## Contents
- [Pydantic v2 validation](#pydantic-v2-validation)
- [Custom base model (verified)](#custom-base-model-verified)
- [ValueError becomes a 422](#valueerror-becomes-a-422)
- [FastAPI response serialization (the double-build)](#fastapi-response-serialization-the-double-build)
- [SQLAlchemy 2.0 async](#sqlalchemy-20-async)
- [Service vs repository](#service-vs-repository)
- [Avoiding N+1 queries](#avoiding-n1-queries)
- [Pagination](#pagination)
- [Naming conventions](#naming-conventions)
- [Alembic migrations](#alembic-migrations)

---

## Pydantic v2 validation

Make schemas the wall that bad data hits first.

```python
from pydantic import BaseModel, EmailStr, Field, AnyUrl
from enum import StrEnum

class MusicBand(StrEnum):
    AEROSMITH = "AEROSMITH"
    QUEEN = "QUEEN"
    ACDC = "AC/DC"

class UserCreate(BaseModel):
    first_name: str = Field(min_length=2, max_length=128)
    username: str = Field(pattern=r"^[A-Za-z0-9-_]+$")
    email: EmailStr
    age: int = Field(ge=18, description="Must be an adult")
    favorite_band: MusicBand | None = None
    website: AnyUrl | None = None
```

## Custom base model (verified)

A shared base model homogenizes config and serialization (e.g. always emit UTC datetimes). The
wildcard `field_serializer("*", ...)` below is valid Pydantic v2 and is exactly what the upstream
best-practices repo uses — it applies to every field, only when serializing to JSON.

```python
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict, field_serializer

class AppBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def _serialize_datetimes(self, value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=ZoneInfo("UTC"))
            return value.strftime("%Y-%m-%dT%H:%M:%S%z")
        return value
```

`from_attributes=True` lets the model read directly from ORM objects; `populate_by_name=True` lets you
populate by field name even when an alias is set.

## ValueError becomes a 422

Inside a request-body schema, raising a plain `ValueError` from a validator produces a detailed,
user-friendly 422 — no manual error formatting needed.

```python
import re
from pydantic import BaseModel, field_validator

class ProfileCreate(BaseModel):
    username: str
    password: str

    @field_validator("password", mode="after")
    @classmethod
    def strong_password(cls, password: str) -> str:
        if not re.match(STRONG_PASSWORD_PATTERN, password):
            raise ValueError(
                "Password must contain a lowercase letter, an uppercase letter, "
                "and a digit or special symbol"
            )
        return password
```

## FastAPI response serialization (the double-build)

When a route declares `response_model=X`, FastAPI runs `jsonable_encoder` on whatever you return,
validates it against `X`, then serializes to JSON. So if you build and return an `X(...)` yourself,
the model is effectively constructed **twice** (once by you, once by FastAPI's validation).

Practical guidance (a tradeoff, not a hard rule): for hot paths you can return the ORM object or a
plain dict and let `response_model` + `from_attributes` build the final Pydantic object once. For most
endpoints the overhead is negligible and returning a typed model is fine and more readable — optimize
this only when profiling says to.

## SQLAlchemy 2.0 async

For new projects, use the async API. Build a single engine and session factory and expose a `get_db`
dependency.

```python
# src/database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.config import settings

engine = create_async_engine(
    settings.database_url,        # postgresql+asyncpg://...
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,           # drop dead connections instead of erroring
    echo=settings.sql_echo,
)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
```

`expire_on_commit=False` keeps attributes usable after commit (otherwise accessing them triggers a
lazy reload that fails outside an async context).

Querying with the 2.0 style:

```python
from sqlalchemy import select

async def get_active_users(db: AsyncSession, limit: int = 100):
    result = await db.execute(
        select(User).where(User.is_active.is_(True)).limit(limit)
    )
    return result.scalars().all()
```

## Service vs repository

Two valid patterns — pick one and be consistent; don't treat either as gospel.

- **Service functions (upstream default, simplest):** a `service.py` module with functions that take a
  session and do the work. Less ceremony, easy to read, perfect for most apps.
- **Repository class (more layering):** a class wrapping the session, useful for large teams, swappable
  data sources, or when you want to mock the data layer wholesale in tests. Costs an extra abstraction
  layer.

```python
# Service style
async def get_active_users(db: AsyncSession, limit: int = 100) -> list[User]:
    res = await db.execute(select(User).where(User.is_active).limit(limit))
    return list(res.scalars().all())

# Repository style
class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    async def get_active(self, limit: int = 100) -> list[User]:
        res = await self.db.execute(select(User).where(User.is_active).limit(limit))
        return list(res.scalars().all())
```

## Avoiding N+1 queries

Accessing a relationship inside a loop issues one extra query per row. Eager-load instead:

```python
from sqlalchemy.orm import selectinload, joinedload

# selectinload: one extra query for the whole collection (great for one-to-many)
res = await db.execute(
    select(Post).options(selectinload(Post.comments)).limit(20)
)

# joinedload: a single JOIN (great for many-to-one / small one-to-one)
res = await db.execute(
    select(Post).options(joinedload(Post.author)).limit(20)
)
```

**SQL-first mindset:** prefer doing joins, aggregation, and even nested-JSON building in the database
rather than pulling thousands of rows into Python loops — the DB is dramatically faster at it.

## Pagination

Never return unbounded lists. Offset pagination is simplest; cursor (keyset) pagination scales to deep
pages without slowing down.

```python
# src/pagination.py
from pydantic import BaseModel, Field

class PageParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int
```

Use `PageParams` as a dependency; for very large tables, paginate by a `WHERE id > :last_id ORDER BY
id LIMIT :n` cursor instead of `OFFSET`, which gets slow as the offset grows.

## Naming conventions

Set explicit DB index/constraint names so they match your database convention rather than SQLAlchemy's
defaults:

```python
from sqlalchemy import MetaData

NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}
metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

Table/column rules: `lower_snake_case`; **singular** table names (`post`, `post_like`,
`user_playlist`); group with a module prefix (`payment_account`, `payment_bill`); `_at` suffix for
datetimes, `_date` suffix for dates; concrete foreign keys (`creator_id`, `post_id`) rather than a bare
`id`.

## Alembic migrations

- Migrations must be **static and reversible**. If a migration depends on generated data, only the data
  should be dynamic — never its structure.
- Generate with **descriptive slugs** that explain the change.
- Set a human-readable file template so history is easy to scan:

```ini
# alembic.ini
file_template = %%(year)d-%%(month).2d-%%(day).2d_%%(slug)s
# e.g. 2026-03-14_add_post_content_index.py
```

For async projects, Alembic's `env.py` must run migrations through the async engine (use
`connection.run_sync(...)` inside an async `run_migrations_online`). The scaffold's
`alembic/env.py` shows the async-aware setup.
