from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings

# SQLite (aiosqlite) does not accept pool_size/max_overflow/pool_pre_ping;
# it uses a single connection per request. We only pass those kwargs when
# the URL points at a real server driver (postgresql+asyncpg).
is_sqlite = settings.database_url.startswith("sqlite")

engine_kwargs: dict = {"echo": settings.sql_echo}
if not is_sqlite:
    engine_kwargs.update(pool_pre_ping=True, pool_size=20, max_overflow=10)

engine = create_async_engine(settings.database_url, **engine_kwargs)

# connect_args={"check_same_thread": False} is required by SQLite when
# the engine is used from multiple async tasks; it's ignored on Postgres.
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
