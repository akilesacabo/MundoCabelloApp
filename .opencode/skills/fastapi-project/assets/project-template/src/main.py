from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.config import settings
from src.database import engine
from src.dependencies import DbSession
from src.exceptions import AppError
from src.items.router import router as items_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: open pools, warm caches, load models here.
    yield
    # Shutdown: dispose the engine so connections close cleanly.
    await engine.dispose()


# Hide interactive docs outside dev-like environments (defense in depth, not security).
SHOW_DOCS_ENVS = {"local", "staging"}
app_configs: dict = {"title": settings.project_name, "lifespan": lifespan}
if settings.environment not in SHOW_DOCS_ENVS:
    app_configs["openapi_url"] = None

app = FastAPI(**app_configs)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
async def ready(db: DbSession) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ready"}


app.include_router(items_router)
