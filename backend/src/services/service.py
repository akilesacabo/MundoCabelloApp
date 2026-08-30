from __future__ import annotations

import re
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.exceptions import BadRequest, Conflict, NotFound
from src.services.models import Area, Promocion, PromocionServicio, ServiceCatalog
from src.services.schemas import (
    AreaCreate,
    AreaUpdate,
    PromotionCreate,
    PromotionUpdate,
    ServiceCreate,
    ServiceUpdate,
)


async def list_areas(db: AsyncSession, *, include_inactive: bool = False) -> list[Area]:
    query = select(Area).order_by(Area.key)
    if not include_inactive:
        query = query.where(Area.activo.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_grouped(db: AsyncSession, *, include_inactive: bool = False) -> list[dict]:
    query = select(Area).options(selectinload(Area.services)).order_by(Area.key)
    if not include_inactive:
        query = query.where(Area.activo.is_(True))
    result = await db.execute(query)
    areas = list(result.scalars().all())
    return [
        {
            "area": a,
            "servicios": sorted(
                [s for s in a.services if include_inactive or s.activo],
                key=lambda s: s.nombre,
            ),
        }
        for a in areas
    ]


async def get_record_or_404(db: AsyncSession, service_id: int) -> ServiceCatalog:
    svc = await db.get(ServiceCatalog, service_id)
    if svc is None:
        raise NotFound(f"servicio {service_id} no existe")
    return svc


async def get_or_404(db: AsyncSession, service_id: int) -> ServiceCatalog:
    svc = await get_record_or_404(db, service_id)
    if not svc.activo:
        raise NotFound(f"servicio {service_id} no existe o está eliminado")
    return svc


async def get_many_or_404(db: AsyncSession, ids: list[int]) -> list[ServiceCatalog]:
    if not ids:
        return []
    result = await db.execute(
        select(ServiceCatalog).where(ServiceCatalog.id.in_(ids), ServiceCatalog.activo.is_(True))
    )
    found = list(result.scalars().all())
    missing = set(ids) - {s.id for s in found}
    if missing:
        raise NotFound(f"servicios no encontrados: {sorted(missing)}")
    return found


async def list_promotions(db: AsyncSession, *, include_inactive: bool = False) -> list[Promocion]:
    query = (
        select(Promocion)
        .options(selectinload(Promocion.servicios).selectinload(PromocionServicio.servicio))
        .order_by(Promocion.nombre)
    )
    if not include_inactive:
        query = query.where(Promocion.activo.is_(True))
    result = await db.execute(query)
    return list(result.scalars().unique().all())


async def get_promotion_components_or_404(db: AsyncSession, ids: list[int]) -> list[Promocion]:
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
    area = await db.get(Area, data.area_key)
    if area is None or not area.activo:
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


async def _validate_promotion_name(
    db: AsyncSession, nombre: str, *, exclude_id: int | None = None
) -> None:
    query = select(Promocion.id).where(Promocion.nombre == nombre)
    if exclude_id is not None:
        query = query.where(Promocion.id != exclude_id)
    if await db.scalar(query) is not None:
        raise BadRequest("ya existe una promoción con ese nombre")


async def _commit_promotion(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if "promocion.nombre" in str(exc.orig).lower():
            raise BadRequest("ya existe una promoción con ese nombre") from exc
        raise


async def create_promotion(db: AsyncSession, data: PromotionCreate) -> Promocion:
    service_ids = [item.service_id for item in data.servicios]
    if len(set(service_ids)) != len(service_ids):
        raise BadRequest("no se puede repetir un servicio dentro de la promoción")
    services = await get_many_or_404(db, service_ids)
    by_id = {service.id: service for service in services}
    nombre = data.nombre.strip().upper()
    await _validate_promotion_name(db, nombre)
    promotion = Promocion(
        nombre=nombre,
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
    await _commit_promotion(db)
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


async def _promotion_record_or_404(db: AsyncSession, promotion_id: int) -> Promocion:
    result = await db.execute(
        select(Promocion)
        .where(Promocion.id == promotion_id)
        .options(selectinload(Promocion.servicios).selectinload(PromocionServicio.servicio))
    )
    promotion = result.scalar_one_or_none()
    if promotion is None:
        raise NotFound(f"promoción {promotion_id} no existe")
    return promotion


async def update_promotion(db: AsyncSession, promotion_id: int, data: PromotionUpdate) -> Promocion:
    promotion = await _promotion_or_404(db, promotion_id)
    service_ids = [item.service_id for item in data.servicios]
    if len(set(service_ids)) != len(service_ids):
        raise BadRequest("no se puede repetir un servicio dentro de la promoción")
    await get_many_or_404(db, service_ids)
    nombre = data.nombre.strip().upper()
    await _validate_promotion_name(db, nombre, exclude_id=promotion_id)
    promotion.nombre = nombre
    promotion.precio_usd = sum((item.precio_usd for item in data.servicios), start=0)
    # La tabla tiene una restricción única por promoción y servicio. Forzamos
    # primero el DELETE de las asociaciones previas para que SQLAlchemy no
    # intente insertar duplicados antes de eliminarlas.
    promotion.servicios.clear()
    await db.flush()
    promotion.servicios = [
        PromocionServicio(
            service_catalog_id=item.service_id,
            precio_usd=item.precio_usd,
        )
        for item in data.servicios
    ]
    await _commit_promotion(db)
    return await _promotion_or_404(db, promotion_id)


async def archive_promotion(db: AsyncSession, promotion_id: int) -> None:
    promotion = await _promotion_or_404(db, promotion_id)
    promotion.activo = False
    await db.commit()


async def restore_promotion(db: AsyncSession, promotion_id: int) -> Promocion:
    promotion = await _promotion_record_or_404(db, promotion_id)
    if promotion.activo:
        raise Conflict("la promoción ya está activa")
    inactive = [item.servicio.nombre for item in promotion.servicios if not item.servicio.activo]
    if inactive:
        raise Conflict(
            "no se puede restaurar la promoción mientras tenga servicios eliminados: "
            + ", ".join(inactive)
        )
    promotion.activo = True
    await db.commit()
    return await _promotion_or_404(db, promotion_id)


async def update_service(db: AsyncSession, service_id: int, data: ServiceUpdate) -> ServiceCatalog:
    service = await get_or_404(db, service_id)
    changes = data.model_dump(exclude_unset=True)
    if "area_key" in changes:
        area = await db.get(Area, changes["area_key"])
        if area is None or not area.activo:
            raise NotFound(f"área {changes['area_key']!r} no existe")
    if "nombre" in changes:
        changes["nombre"] = changes["nombre"].strip().upper()
    for field, value in changes.items():
        setattr(service, field, value)
    await db.commit()
    await db.refresh(service)
    return service


async def archive_service(db: AsyncSession, service_id: int) -> None:
    service = await get_or_404(db, service_id)
    active_promotion = await db.scalar(
        select(Promocion.id)
        .join(PromocionServicio)
        .where(
            PromocionServicio.service_catalog_id == service_id,
            Promocion.activo.is_(True),
        )
        .limit(1)
    )
    if active_promotion is not None:
        raise Conflict(
            "el servicio pertenece a una promoción activa; edita o elimina la promoción primero"
        )
    service.activo = False
    await db.commit()


async def restore_service(db: AsyncSession, service_id: int) -> ServiceCatalog:
    service = await get_record_or_404(db, service_id)
    if service.activo:
        raise Conflict("el servicio ya está activo")
    area = await db.get(Area, service.area_key)
    if area is None or not area.activo:
        raise Conflict("restaura primero el área asociada al servicio")
    service.activo = True
    await db.commit()
    await db.refresh(service)
    return service


def _area_key(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.strip())
    ascii_name = "".join(char for char in normalized if not unicodedata.combining(char))
    key = re.sub(r"[^a-z0-9]+", "_", ascii_name.casefold()).strip("_")[:32]
    if len(key) < 2:
        raise BadRequest("el nombre del área no produce una clave válida")
    return key


async def _validate_area_name(
    db: AsyncSession, name: str, *, exclude_key: str | None = None
) -> None:
    query = select(Area.key).where(func.lower(Area.name) == name.casefold())
    if exclude_key is not None:
        query = query.where(Area.key != exclude_key)
    if await db.scalar(query) is not None:
        raise Conflict("ya existe un área con ese nombre")


async def create_area(db: AsyncSession, data: AreaCreate) -> Area:
    name = data.name.strip()
    await _validate_area_name(db, name)
    key = _area_key(name)
    if await db.get(Area, key) is not None:
        raise Conflict(f"ya existe un área con la clave {key!r}")
    area = Area(key=key, name=name, color=data.color.lower(), activo=True)
    db.add(area)
    await db.commit()
    await db.refresh(area)
    return area


async def update_area(db: AsyncSession, key: str, data: AreaUpdate) -> Area:
    area = await db.get(Area, key)
    if area is None or not area.activo:
        raise NotFound(f"área {key!r} no existe o está eliminada")
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        await _validate_area_name(db, changes["name"], exclude_key=key)
    if "color" in changes:
        changes["color"] = changes["color"].lower()
    for field, value in changes.items():
        setattr(area, field, value)
    await db.commit()
    await db.refresh(area)
    return area


async def archive_area(db: AsyncSession, key: str) -> None:
    area = await db.get(Area, key)
    if area is None or not area.activo:
        raise NotFound(f"área {key!r} no existe o está eliminada")
    if (
        await db.scalar(
            select(ServiceCatalog.id)
            .where(ServiceCatalog.area_key == key, ServiceCatalog.activo.is_(True))
            .limit(1)
        )
        is not None
    ):
        raise Conflict("el área todavía tiene servicios activos")
    from src.staff.models import Staff, staff_area

    if (
        await db.scalar(
            select(Staff.numero)
            .join(staff_area, staff_area.c.staff_numero == Staff.numero)
            .where(staff_area.c.area_key == key, Staff.activo.is_(True))
            .limit(1)
        )
        is not None
    ):
        raise Conflict("el área todavía tiene especialistas activos")
    area.activo = False
    await db.commit()


async def restore_area(db: AsyncSession, key: str) -> Area:
    area = await db.get(Area, key)
    if area is None:
        raise NotFound(f"área {key!r} no existe")
    if area.activo:
        raise Conflict("el área ya está activa")
    area.activo = True
    await db.commit()
    await db.refresh(area)
    return area
