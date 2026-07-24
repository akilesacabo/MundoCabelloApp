from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.exceptions import NotFound
from src.services.models import Area, ServiceCatalog
from src.services.schemas import ServiceCreate, ServiceUpdate


async def list_areas(db: AsyncSession) -> list[Area]:
    result = await db.execute(select(Area).order_by(Area.key))
    return list(result.scalars().all())


async def list_grouped(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Area).options(selectinload(Area.services)).order_by(Area.key)
    )
    areas = list(result.scalars().all())
    return [
        {
            "area": a,
            "servicios": sorted(a.services, key=lambda s: s.nombre),
        }
        for a in areas
    ]


async def get_or_404(db: AsyncSession, service_id: int) -> ServiceCatalog:
    svc = await db.get(ServiceCatalog, service_id)
    if svc is None:
        raise NotFound(f"servicio {service_id} no existe")
    return svc


async def get_many_or_404(db: AsyncSession, ids: list[int]) -> list[ServiceCatalog]:
    if not ids:
        raise NotFound("debe indicar al menos un servicio")
    result = await db.execute(select(ServiceCatalog).where(ServiceCatalog.id.in_(ids)))
    found = list(result.scalars().all())
    missing = set(ids) - {s.id for s in found}
    if missing:
        raise NotFound(f"servicios no encontrados: {sorted(missing)}")
    return found


async def create_service(db: AsyncSession, data: ServiceCreate) -> ServiceCatalog:
    if await db.get(Area, data.area_key) is None:
        raise NotFound(f"área {data.area_key!r} no existe")
    service = ServiceCatalog(
        nombre=data.nombre.strip().upper(),
        area_key=data.area_key,
        precio_usd=data.precio_usd,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


async def update_service(
    db: AsyncSession, service_id: int, data: ServiceUpdate
) -> ServiceCatalog:
    service = await get_or_404(db, service_id)
    changes = data.model_dump(exclude_unset=True)
    if "area_key" in changes and await db.get(Area, changes["area_key"]) is None:
        raise NotFound(f"área {changes['area_key']!r} no existe")
    if "nombre" in changes:
        changes["nombre"] = changes["nombre"].strip().upper()
    for field, value in changes.items():
        setattr(service, field, value)
    await db.commit()
    await db.refresh(service)
    return service
