from typing import Annotated

from fastapi import APIRouter, Query, status

from src.auth.dependencies import AdminUser, CurrentUser, OptionalUser
from src.dependencies import DbSession
from src.exceptions import PermissionDenied
from src.turnos import service as turnos_service
from src.turnos.schemas import (
    AssignManyRequest,
    AssignRequest,
    ChangeSpecialistRequest,
    CheckInRequest,
    ClienteProfileDetail,
    ClienteProfileRead,
    ClienteProfileSummary,
    ClienteRead,
    PublicQueueRead,
    QueuePositionRead,
    SituacionUpdate,
    TurnoDetailsUpdate,
)

router = APIRouter(prefix="/queue", tags=["turnos"])


@router.post(
    "/checkin",
    response_model=ClienteRead,
    status_code=status.HTTP_201_CREATED,
)
async def check_in(
    payload: CheckInRequest, db: DbSession, user: OptionalUser
) -> ClienteRead:
    return await turnos_service.check_in(db, payload, registered_by=user)


@router.get("", response_model=list[ClienteRead])
async def list_turnos(
    db: DbSession,
    admin: AdminUser,
    estado: Annotated[
        str | None, Query(description="en_espera | en_atencion | finalizado")
    ] = None,
) -> list[ClienteRead]:
    return await turnos_service.list_clientes(db, estado=estado)


@router.get("/public/status", response_model=PublicQueueRead)
async def get_public_queue(db: DbSession) -> PublicQueueRead:
    return await turnos_service.public_queue(db)


@router.get("/position-search", response_model=list[QueuePositionRead])
async def position_search(
    q: Annotated[str, Query(min_length=1, max_length=128)],
    db: DbSession,
    admin: AdminUser,
) -> list[QueuePositionRead]:
    return await turnos_service.queue_positions(db, q)


@router.get("/specialist/mine", response_model=list[ClienteRead])
async def specialist_queue(db: DbSession, user: CurrentUser) -> list[ClienteRead]:
    if user.role != "especialista":
        raise PermissionDenied("Esta vista corresponde a especialistas.")
    return await turnos_service.assigned_to_staff(db, int(user.subject))


@router.get("/client-search", response_model=list[ClienteProfileRead])
async def search_clientes(
    q: Annotated[str, Query(min_length=4, max_length=30)],
    db: DbSession,
) -> list[ClienteProfileRead]:
    """Autocompletado de recepción. Devuelve como máximo ocho coincidencias."""
    return await turnos_service.search_profiles(db, q)


@router.get("/clients", response_model=list[ClienteProfileSummary])
async def list_client_profiles(
    db: DbSession, admin: AdminUser
) -> list[ClienteProfileSummary]:
    return await turnos_service.list_profiles(db)


@router.get("/clients/{profile_id}", response_model=ClienteProfileDetail)
async def get_client_profile(
    profile_id: int, db: DbSession, admin: AdminUser
) -> ClienteProfileDetail:
    return await turnos_service.get_profile_detail(db, profile_id)


@router.get("/{cliente_id}", response_model=ClienteRead)
async def get_turno(cliente_id: int, db: DbSession) -> ClienteRead:
    return await turnos_service.get_cliente(db, cliente_id)


@router.post(
    "/{cliente_id}/services/{servicio_id}/assign",
    response_model=ClienteRead,
)
async def assign_service(
    cliente_id: int,
    servicio_id: int,
    payload: AssignRequest,
    db: DbSession,
    admin: AdminUser,
) -> ClienteRead:
    return await turnos_service.assign_service(db, cliente_id, servicio_id, payload)


@router.post("/{cliente_id}/services/assign-many", response_model=ClienteRead)
async def assign_many(
    cliente_id: int, payload: AssignManyRequest, db: DbSession, admin: AdminUser
) -> ClienteRead:
    return await turnos_service.assign_many(db, cliente_id, payload)


@router.post(
    "/{cliente_id}/services/{servicio_id}/finish",
    response_model=ClienteRead,
)
async def finish_service(
    cliente_id: int, servicio_id: int, db: DbSession, user: CurrentUser
) -> ClienteRead:
    if user.role == "especialista":
        turno = await turnos_service.get_cliente(db, cliente_id)
        servicio = next((s for s in turno.servicios if s.id == servicio_id), None)
        if servicio is None or servicio.staff_numero != int(user.subject):
            raise PermissionDenied("El servicio no está asignado a este especialista.")
    return await turnos_service.finish_service(db, cliente_id, servicio_id)


async def _ensure_service_owner(
    cliente_id: int, servicio_id: int, db: DbSession, user: CurrentUser
) -> None:
    if user.role != "especialista":
        return
    turno = await turnos_service.get_cliente(db, cliente_id)
    servicio = next((s for s in turno.servicios if s.id == servicio_id), None)
    if servicio is None or servicio.staff_numero != int(user.subject):
        raise PermissionDenied("El servicio no está asignado a este especialista.")


@router.post(
    "/{cliente_id}/services/{servicio_id}/rest",
    response_model=ClienteRead,
)
async def rest_service(
    cliente_id: int, servicio_id: int, db: DbSession, user: CurrentUser
) -> ClienteRead:
    await _ensure_service_owner(cliente_id, servicio_id, db, user)
    return await turnos_service.rest_service(db, cliente_id, servicio_id)


@router.post(
    "/{cliente_id}/services/{servicio_id}/resume",
    response_model=ClienteRead,
)
async def resume_service(
    cliente_id: int, servicio_id: int, db: DbSession, user: CurrentUser
) -> ClienteRead:
    await _ensure_service_owner(cliente_id, servicio_id, db, user)
    return await turnos_service.resume_service(db, cliente_id, servicio_id)


@router.post(
    "/{cliente_id}/services/{servicio_id}/change-specialist",
    response_model=ClienteRead,
)
async def change_specialist(
    cliente_id: int,
    servicio_id: int,
    payload: ChangeSpecialistRequest,
    db: DbSession,
    admin: AdminUser,
) -> ClienteRead:
    return await turnos_service.change_specialist(db, cliente_id, servicio_id, payload)


@router.post("/lookup", response_model=ClienteProfileRead)
async def lookup_cliente(cedula: str, db: DbSession) -> ClienteProfileRead:
    return await turnos_service.find_profile(db, cedula)


@router.patch("/{cliente_id}/situacion", response_model=ClienteRead)
async def set_situacion(
    cliente_id: int, payload: SituacionUpdate, db: DbSession, admin: AdminUser
) -> ClienteRead:
    return await turnos_service.update_situacion(db, cliente_id, payload)


@router.patch("/{cliente_id}/details", response_model=ClienteRead)
async def set_turno_details(
    cliente_id: int,
    payload: TurnoDetailsUpdate,
    db: DbSession,
    admin: AdminUser,
) -> ClienteRead:
    return await turnos_service.update_details(db, cliente_id, payload)
