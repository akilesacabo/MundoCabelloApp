from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from src.auth.router import router as auth_router
from src.config import settings
from src.database import engine
from src.dependencies import DbSession
from src.exceptions import AppError
from src.historial.router import router as historial_router
from src.services.router import router as services_router
from src.staff.router import router as staff_router
from src.turnos.router import router as turnos_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


SHOW_DOCS_ENVS = {"local", "staging"}
app_configs: dict = {"title": settings.project_name, "lifespan": lifespan}
if settings.environment not in SHOW_DOCS_ENVS:
    app_configs["openapi_url"] = None

app = FastAPI(**app_configs)
app_dir = Path(__file__).resolve().parents[2] / "app"

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


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/app/login.html")


app.mount("/app", StaticFiles(directory=app_dir, html=False), name="app")
app.include_router(services_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(staff_router, prefix="/api")
app.include_router(turnos_router, prefix="/api")
app.include_router(historial_router, prefix="/api")
