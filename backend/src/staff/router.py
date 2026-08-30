from typing import Annotated

from fastapi import APIRouter, Query

from src.auth.dependencies import AdminUser, OptionalUser
from src.dependencies import DbSession
from src.exceptions import PermissionDenied
from src.staff import service as staff_service
from src.staff.schemas import ManualStatusUpdate, StaffCreate, StaffRead, StaffUpdate

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("", response_model=list[StaffRead])
async def list_staff(
    db: DbSession,
    user: OptionalUser,
    area: Annotated[str | None, Query(description="Filtra por área (peluqueria, etc.)")] = None,
    status: Annotated[
        str | None, Query(description="Filtra por estado efectivo: disponible|ocupado|break")
    ] = None,
    include_inactive: bool = False,
) -> list[StaffRead]:
    if include_inactive and (user is None or user.role != "admin"):
        raise PermissionDenied("Solo administración puede consultar especialistas eliminadas.")
    return await staff_service.list_staff(
        db, area=area, status=status, include_inactive=include_inactive
    )


@router.get("/eligible", response_model=list[StaffRead])
async def eligible(area: str, db: DbSession) -> list[StaffRead]:
    """Personal DISPONIBLE que cubre el área indicada."""
    return await staff_service.eligible_for(db, area)


@router.get("/{numero}", response_model=StaffRead)
async def get_staff(numero: int, db: DbSession) -> StaffRead:
    return await staff_service.get_read_or_404(db, numero)


@router.patch("/{numero}/manual-status", response_model=StaffRead)
async def update_manual_status(
    numero: int, data: ManualStatusUpdate, db: DbSession, admin: AdminUser
) -> StaffRead:
    return await staff_service.set_manual_status(db, numero, data)


@router.post("/{numero}/toggle-en-prueba", response_model=StaffRead)
async def toggle_en_prueba(numero: int, db: DbSession, admin: AdminUser) -> StaffRead:
    return await staff_service.toggle_en_prueba(db, numero)


@router.post("", response_model=StaffRead, status_code=201)
async def create_staff(data: StaffCreate, db: DbSession, admin: AdminUser) -> StaffRead:
    return await staff_service.create_staff(db, data)


@router.patch("/{numero}", response_model=StaffRead)
async def edit_staff(numero: int, data: StaffUpdate, db: DbSession, admin: AdminUser) -> StaffRead:
    return await staff_service.update_staff(db, numero, data)


@router.delete("/{numero}", status_code=204)
async def delete_staff(numero: int, db: DbSession, admin: AdminUser) -> None:
    await staff_service.archive_staff(db, numero)


@router.post("/{numero}/restore", response_model=StaffRead)
async def restore_staff(numero: int, db: DbSession, admin: AdminUser) -> StaffRead:
    return await staff_service.restore_staff(db, numero)
