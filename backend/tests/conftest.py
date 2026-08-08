"""Fixture E2E con SQLite en memoria y un mini-seed que refleja el modelo v2."""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# In-memory DB antes de importar la app.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from src.database import async_session, engine  # noqa: E402
from src.main import app  # noqa: E402
from src.models import Base  # noqa: E402
from src.services.constants import AreaKey  # noqa: E402
from src.services.models import Area, ServiceCatalog  # noqa: E402
from src.staff.constants import ManualStatus  # noqa: E402
from src.staff.models import Staff, staff_area  # noqa: E402


@pytest_asyncio.fixture
async def api() -> AsyncGenerator[dict, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # 2 áreas: peluquería y hidratación
        db.add_all([
            Area(key=AreaKey.PELUQUERIA, name="Peluquería", color="#ffb4ab"),
            Area(key=AreaKey.HIDRATACION, name="Hidratación", color="#a3defe"),
            Area(key=AreaKey.MANICURE, name="Manicure", color="#f6cc87"),
        ])
        # Catálogo mínimo
        corte = ServiceCatalog(nombre="CORTE DAMA", area_key=AreaKey.PELUQUERIA, precio_usd=15)
        hidra = ServiceCatalog(
            nombre="HIDRATACION SALERM",
            area_key=AreaKey.HIDRATACION,
            precio_usd=25,
        )
        unas = ServiceCatalog(nombre="MANICURE EXPRESS", area_key=AreaKey.MANICURE, precio_usd=10)
        db.add_all([corte, hidra, unas])

        # 3 staff
        ana = Staff(
            numero=1, alias="Ana", nombre="Ana R", cedula="V-1", initials="AR",
            manual_status=ManualStatus.DISPONIBLE, en_prueba=False,
        )
        beto = Staff(  # sólo hidratación
            numero=2, alias="Beto", nombre="Beto S", cedula="V-2", initials="BS",
            manual_status=ManualStatus.DISPONIBLE, en_prueba=False,
        )
        cami = Staff(  # en BREAK
            numero=3, alias="Cami", nombre="Cami T", cedula="V-3", initials="CT",
            manual_status=ManualStatus.BREAK, en_prueba=False,
        )
        db.add_all([ana, beto, cami])
        await db.flush()

        # M:N: Ana cubre peluquería + hidratación; Beto sólo hidratación; Cami sólo peluquería
        for sn, ak in [
            (1, AreaKey.PELUQUERIA), (1, AreaKey.HIDRATACION),
            (1, AreaKey.MANICURE),
            (2, AreaKey.HIDRATACION),
            (3, AreaKey.PELUQUERIA),
        ]:
            await db.execute(staff_area.insert().values(staff_numero=sn, area_key=ak))

        await db.commit()
        ids = {"corte_id": corte.id, "hidra_id": hidra.id, "unas_id": unas.id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/auth/login",
            json={
                "role": "admin",
                "username": "admin",
                "password": "admin-demo",
            },
        )
        admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        yield {"ac": ac, "admin_headers": admin_headers, **ids}

    await engine.dispose()
