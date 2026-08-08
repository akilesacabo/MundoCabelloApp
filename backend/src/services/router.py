from fastapi import APIRouter

from src.auth.dependencies import AdminUser
from src.dependencies import DbSession
from src.services import service as services_service
from src.services.schemas import (
    AreaRead,
    PromotionCreate,
    PromotionRead,
    PromotionServiceRead,
    ServiceCreate,
    ServiceRead,
    ServicesGrouped,
    ServiceUpdate,
)

router = APIRouter(prefix="/services", tags=["services"])


@router.get("/areas", response_model=list[AreaRead])
async def list_areas(db: DbSession) -> list[AreaRead]:
    return [AreaRead.model_validate(a) for a in await services_service.list_areas(db)]


@router.get("", response_model=list[ServicesGrouped])
async def list_services_grouped(db: DbSession) -> list[ServicesGrouped]:
    grouped = await services_service.list_grouped(db)
    return [
        ServicesGrouped(
            area=AreaRead.model_validate(g["area"]),
            servicios=[ServiceRead.model_validate(s) for s in g["servicios"]],
        )
        for g in grouped
    ]


@router.get("/promotions", response_model=list[PromotionRead])
async def list_promotions(db: DbSession) -> list[PromotionRead]:
    return [
        PromotionRead(
            id=promotion.id,
            nombre=promotion.nombre,
            precio_usd=promotion.precio_usd,
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
        for promotion in await services_service.list_promotions(db)
    ]


@router.post("", response_model=ServiceRead, status_code=201)
async def create_service(
    data: ServiceCreate, db: DbSession, admin: AdminUser
) -> ServiceRead:
    return ServiceRead.model_validate(await services_service.create_service(db, data))


@router.post("/promotions", response_model=PromotionRead, status_code=201)
async def create_promotion(
    data: PromotionCreate, db: DbSession, admin: AdminUser
) -> PromotionRead:
    promotion = await services_service.create_promotion(db, data)
    return PromotionRead(
        id=promotion.id,
        nombre=promotion.nombre,
        precio_usd=promotion.precio_usd,
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


@router.patch("/{service_id}", response_model=ServiceRead)
async def edit_service(
    service_id: int, data: ServiceUpdate, db: DbSession, admin: AdminUser
) -> ServiceRead:
    service = await services_service.update_service(db, service_id, data)
    return ServiceRead.model_validate(service)
