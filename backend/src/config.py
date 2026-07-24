from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "El Mundo del Cabello — API"
    environment: str = "local"

    # SQLite in dev (no asyncpg needed). In production, point this at
    # `postgresql+asyncpg://user:pass@host:5432/db` — the rest of the
    # code is driver-agnostic because everything goes through asyncpg
    # OR aiosqlite via the same AsyncSession API.
    database_url: str = "sqlite+aiosqlite:///./peluq.db"
    sql_echo: bool = False

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

    # PIN de administrador para reasignar un servicio a mitad de turno.
    # Default `1234` para dev; sobrescribir con env var en prod.
    admin_pin: str = "1234"

    # Autenticación MVP. Todos estos valores deben sobrescribirse en producción.
    admin_username: str = "admin"
    admin_password: str = "admin-demo"
    auth_secret: str = "change-me-in-production"
    auth_token_ttl_minutes: int = 480

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )


settings = Settings()
