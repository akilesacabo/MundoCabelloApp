from fastapi import APIRouter

from src.auth.dependencies import AdminUser, OptionalUser
from src.dependencies import DbSession
from src.exceptions import PermissionDenied
from src.services import service as services_service
from src.services.schemas import (
    AreaCreate,
    AreaRead,
    AreaUpdate,
    PromotionCreate,
    PromotionRead,
    PromotionServiceRead,
    PromotionUpdate,
    ServiceCreate,
    ServiceRead,
    ServicesGrouped,
    ServiceUpdate,
)

router = APIRouter(prefix="/services", tags=["services"])


def _promotion_read(promotion) -> PromotionRead:
    return PromotionRead(
        id=promotion.id,
        nombre=promotion.nombre,
        precio_usd=promotion.precio_usd,
        activo=promotion.activo,
        servicios=[
            PromotionServiceRead(
                service_id=item.service_catalog_id,
                nombre=item.servicio.nombre,
                area_key=item.servicio.area_key,
                precio_usd=item.precio_usd,
            )
            for item in promotion.servicios
        ],
    )


def _authorize_inactive(include_inactive: bool, user) -> None:
    if include_inactive and (user is None or user.role != "admin"):
        raise PermissionDenied("Solo administración puede consultar registros eliminados.")


@router.get("/areas", response_model=list[AreaRead])
async def list_areas(
    db: DbSession, user: OptionalUser, include_inactive: bool = False
) -> list[AreaRead]:
    _authorize_inactive(include_inactive, user)
    return [
        AreaRead.model_validate(a)
        for a in await services_service.list_areas(db, include_inactive=include_inactive)
    ]


@router.post("/areas", response_model=AreaRead, status_code=201)
async def create_area(data: AreaCreate, db: DbSession, admin: AdminUser) -> AreaRead:
    return AreaRead.model_validate(await services_service.create_area(db, data))


@router.patch("/areas/{key}", response_model=AreaRead)
async def update_area(key: str, data: AreaUpdate, db: DbSession, admin: AdminUser) -> AreaRead:
    return AreaRead.model_validate(await services_service.update_area(db, key, data))


@router.delete("/areas/{key}", status_code=204)
async def delete_area(key: str, db: DbSession, admin: AdminUser) -> None:
    await services_service.archive_area(db, key)


@router.post("/areas/{key}/restore", response_model=AreaRead)
async def restore_area(key: str, db: DbSession, admin: AdminUser) -> AreaRead:
    return AreaRead.model_validate(await services_service.restore_area(db, key))


@router.get("", response_model=list[ServicesGrouped])
async def list_services_grouped(
    db: DbSession, user: OptionalUser, include_inactive: bool = False
) -> list[ServicesGrouped]:
    _authorize_inactive(include_inactive, user)
    grouped = await services_service.list_grouped(db, include_inactive=include_inactive)
    return [
        ServicesGrouped(
            area=AreaRead.model_validate(g["area"]),
            servicios=[ServiceRead.model_validate(s) for s in g["servicios"]],
        )
        for g in grouped
    ]


@router.get("/promotions", response_model=list[PromotionRead])
async def list_promotions(
    db: DbSession, user: OptionalUser, include_inactive: bool = False
) -> list[PromotionRead]:
    _authorize_inactive(include_inactive, user)
    return [
        _promotion_read(promotion)
        for promotion in await services_service.list_promotions(
            db, include_inactive=include_inactive
        )
    ]


@router.post("", response_model=ServiceRead, status_code=201)
async def create_service(data: ServiceCreate, db: DbSession, admin: AdminUser) -> ServiceRead:
    return ServiceRead.model_validate(await services_service.create_service(db, data))


@router.post("/promotions", response_model=PromotionRead, status_code=201)
async def create_promotion(data: PromotionCreate, db: DbSession, admin: AdminUser) -> PromotionRead:
    promotion = await services_service.create_promotion(db, data)
    return _promotion_read(promotion)


@router.patch("/promotions/{promotion_id}", response_model=PromotionRead)
async def update_promotion(
    promotion_id: int, data: PromotionUpdate, db: DbSession, admin: AdminUser
) -> PromotionRead:
    return _promotion_read(await services_service.update_promotion(db, promotion_id, data))


@router.delete("/promotions/{promotion_id}", status_code=204)
async def archive_promotion(promotion_id: int, db: DbSession, admin: AdminUser) -> None:
    await services_service.archive_promotion(db, promotion_id)


@router.post("/promotions/{promotion_id}/restore", response_model=PromotionRead)
async def restore_promotion(promotion_id: int, db: DbSession, admin: AdminUser) -> PromotionRead:
    return _promotion_read(await services_service.restore_promotion(db, promotion_id))


@router.patch("/{service_id}", response_model=ServiceRead)
async def edit_service(
    service_id: int, data: ServiceUpdate, db: DbSession, admin: AdminUser
) -> ServiceRead:
    service = await services_service.update_service(db, service_id, data)
    return ServiceRead.model_validate(service)


@router.delete("/{service_id}", status_code=204)
async def delete_service(service_id: int, db: DbSession, admin: AdminUser) -> None:
    await services_service.archive_service(db, service_id)


@router.post("/{service_id}/restore", response_model=ServiceRead)
async def restore_service(service_id: int, db: DbSession, admin: AdminUser) -> ServiceRead:
    return ServiceRead.model_validate(await services_service.restore_service(db, service_id))
