"""Seed real desde `mockups/data.json`.

Corrida:
    .venv/bin/python -m src.seed

Idempotente: refresca áreas, servicios y datos maestros de los especialistas.
Conserva el estado manual y la marca de período de prueba de perfiles existentes.
"""
from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import async_session
from src.services.models import Area, ServiceCatalog
from src.staff.constants import ManualStatus
from src.staff.models import Staff

DATA_PATH = Path(__file__).resolve().parents[2] / "mockups" / "data.json"


def _manual_status_for(idx: int) -> str:
    return ManualStatus.BREAK if idx % 7 == 0 else ManualStatus.DISPONIBLE


def _en_prueba_for(numero: int) -> bool:
    return numero % 19 == 0


def _load_data() -> dict:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"No encuentro {DATA_PATH}. El seed depende de la fuente de verdad "
            "en mockups/data.json."
        )
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _unique_staff_rows(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Conserva todas las personas y asigna un número técnico provisional a duplicados.

    Nunca lo hace en silencio: devuelve advertencias para que el operador pueda corregir
    la nómina fuente con el cliente.
    """
    used: set[int] = set()
    next_number = max(row["numero"] for row in rows) + 1
    normalized: list[dict] = []
    warnings: list[str] = []
    for source in rows:
        row = source.copy()
        if row["numero"] in used:
            original = row["numero"]
            while next_number in used:
                next_number += 1
            row["numero"] = next_number
            warnings.append(
                f"número duplicado {original}: {row['alias']} usa provisional {next_number}"
            )
            next_number += 1
        used.add(row["numero"])
        normalized.append(row)
    return normalized, warnings


async def upsert_areas(db: AsyncSession, data: dict) -> None:
    existing = {a.key: a for a in (await db.execute(select(Area))).scalars().all()}
    for a in data["areas"]:
        cur = existing.get(a["key"])
        if cur is None:
            db.add(Area(key=a["key"], name=a["name"], color=a["color"]))
        else:
            cur.name = a["name"]
            cur.color = a["color"]
    await db.commit()


async def upsert_services(db: AsyncSession, data: dict) -> int:
    """Upsert por (nombre, area_key). No borra los que ya no estén en el JSON
    para no romper referencias históricas de tickets ya finalizados.
    """
    existing = {
        (s.nombre, s.area_key): s
        for s in (await db.execute(select(ServiceCatalog))).scalars().all()
    }
    added = 0
    for sv in data["servicios"]:
        key = (sv["nombre"], sv["area"])
        precio = Decimal(str(sv["precio_usd"]))
        cur = existing.get(key)
        if cur is None:
            db.add(
                ServiceCatalog(
                    nombre=sv["nombre"], area_key=sv["area"], precio_usd=precio
                )
            )
            added += 1
        else:
            cur.precio_usd = precio
    await db.commit()
    return added


async def sync_staff(db: AsyncSession, data: dict) -> int:
    """Concilia la nómina explícita sin borrar personal ni pisar su estado."""
    staff_rows, warnings = _unique_staff_rows(data["staff"])
    for warning in warnings:
        print(f"ADVERTENCIA seed: {warning}")

    existing = {
        staff.numero: staff
        for staff in (
            await db.execute(select(Staff).options(selectinload(Staff.areas)))
        ).scalars()
    }
    area_by_key = {
        area.key: area for area in (await db.execute(select(Area))).scalars()
    }
    added = 0
    for idx, s in enumerate(staff_rows):
        staff = existing.get(s["numero"])
        if staff is None:
            staff = Staff(
                numero=s["numero"],
                manual_status=_manual_status_for(idx),
                en_prueba=_en_prueba_for(s["numero"]),
            )
            db.add(staff)
            added += 1
        staff.alias = s["alias"]
        staff.nombre = s["nombre"]
        staff.cedula = s["cedula"]
        staff.initials = s["initials"]
        staff.areas = [area_by_key[key] for key in s["areas"]]
    await db.commit()
    return added


async def main() -> None:
    from sqlalchemy import func

    data = _load_data()
    async with async_session() as db:
        await upsert_areas(db, data)
        n_new_services = await upsert_services(db, data)
        n_new_staff = await sync_staff(db, data)

        na = await db.scalar(select(func.count()).select_from(Area)) or 0
        ns = await db.scalar(select(func.count()).select_from(ServiceCatalog)) or 0
        nst = await db.scalar(select(func.count()).select_from(Staff)) or 0
        print(
            f"seed OK: areas={na} servicios={ns} staff={nst} "
            f"(nuevos servicios: {n_new_services}, nuevo staff: {n_new_staff})"
        )


if __name__ == "__main__":
    asyncio.run(main())
