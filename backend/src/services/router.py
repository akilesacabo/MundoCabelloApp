from fastapi import APIRouter

from src.auth.dependencies import AdminUser
from src.dependencies import DbSession
from src.services import service as services_service
from src.services.schemas import (
    AreaRead,
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


@router.post("", response_model=ServiceRead, status_code=201)
async def create_service(
    data: ServiceCreate, db: DbSession, admin: AdminUser
) -> ServiceRead:
    return ServiceRead.model_validate(await services_service.create_service(db, data))


@router.patch("/{service_id}", response_model=ServiceRead)
async def edit_service(
    service_id: int, data: ServiceUpdate, db: DbSession, admin: AdminUser
) -> ServiceRead:
    service = await services_service.update_service(db, service_id, data)
    return ServiceRead.model_validate(service)
