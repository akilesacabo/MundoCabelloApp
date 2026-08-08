from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.exceptions import BadRequest, NotFound
from src.services.models import Area, Promocion, PromocionServicio, ServiceCatalog
from src.services.schemas import (
    PromotionCreate,
    PromotionUpdate,
    ServiceCreate,
    ServiceUpdate,
)


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
        return []
    result = await db.execute(select(ServiceCatalog).where(ServiceCatalog.id.in_(ids)))
    found = list(result.scalars().all())
    missing = set(ids) - {s.id for s in found}
    if missing:
        raise NotFound(f"servicios no encontrados: {sorted(missing)}")
    return found


async def list_promotions(db: AsyncSession) -> list[Promocion]:
    result = await db.execute(
        select(Promocion)
        .where(Promocion.activo.is_(True))
        .options(selectinload(Promocion.servicios).selectinload(PromocionServicio.servicio))
        .order_by(Promocion.nombre)
    )
    return list(result.scalars().unique().all())


async def get_promotion_components_or_404(
    db: AsyncSession, ids: list[int]
) -> list[Promocion]:
    if not ids:
        return []
    result = await db.execute(
        select(Promocion)
        .where(Promocion.id.in_(ids), Promocion.activo.is_(True))
        .options(selectinload(Promocion.servicios).selectinload(PromocionServicio.servicio))
    )
    promotions = list(result.scalars().unique().all())
    missing = set(ids) - {promotion.id for promotion in promotions}
    if missing:
        raise NotFound(f"promociones no encontradas: {sorted(missing)}")
    if any(not promotion.servicios for promotion in promotions):
        raise BadRequest("una promoción debe contener al menos un servicio")
    return promotions


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


async def create_promotion(db: AsyncSession, data: PromotionCreate) -> Promocion:
    service_ids = [item.service_id for item in data.servicios]
    if len(set(service_ids)) != len(service_ids):
        raise BadRequest("no se puede repetir un servicio dentro de la promoción")
    services = await get_many_or_404(db, service_ids)
    by_id = {service.id: service for service in services}
    promotion = Promocion(
        nombre=data.nombre.strip().upper(),
        precio_usd=sum((item.precio_usd for item in data.servicios), start=0),
        servicios=[
            PromocionServicio(
                service_catalog_id=item.service_id,
                precio_usd=item.precio_usd,
            )
            for item in data.servicios
            if item.service_id in by_id
        ],
    )
    db.add(promotion)
    await db.commit()
    result = await db.execute(
        select(Promocion)
        .where(Promocion.id == promotion.id)
        .options(selectinload(Promocion.servicios).selectinload(PromocionServicio.servicio))
    )
    return result.scalar_one()


async def _promotion_or_404(db: AsyncSession, promotion_id: int) -> Promocion:
    result = await db.execute(
        select(Promocion)
        .where(Promocion.id == promotion_id, Promocion.activo.is_(True))
        .options(selectinload(Promocion.servicios).selectinload(PromocionServicio.servicio))
    )
    promotion = result.scalar_one_or_none()
    if promotion is None:
        raise NotFound(f"promoción {promotion_id} no existe o está archivada")
    return promotion


async def update_promotion(
    db: AsyncSession, promotion_id: int, data: PromotionUpdate
) -> Promocion:
    promotion = await _promotion_or_404(db, promotion_id)
    service_ids = [item.service_id for item in data.servicios]
    if len(set(service_ids)) != len(service_ids):
        raise BadRequest("no se puede repetir un servicio dentro de la promoción")
    await get_many_or_404(db, service_ids)
    promotion.nombre = data.nombre.strip().upper()
    promotion.precio_usd = sum((item.precio_usd for item in data.servicios), start=0)
    promotion.servicios[:] = [
        PromocionServicio(
            service_catalog_id=item.service_id,
            precio_usd=item.precio_usd,
        )
        for item in data.servicios
    ]
    await db.commit()
    return await _promotion_or_404(db, promotion_id)


async def archive_promotion(db: AsyncSession, promotion_id: int) -> None:
    promotion = await _promotion_or_404(db, promotion_id)
    promotion.activo = False
    await db.commit()


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
