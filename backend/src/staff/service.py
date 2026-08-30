"""Staff con áreas múltiples y estado efectivo.

El panel guarda DISPONIBLE, OCUPADO, BREAK o ALMORZANDO. Un servicio EN_ATENCION
tiene prioridad y mantiene el estado efectivo OCUPADO.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.exceptions import Conflict, NotFound
from src.services.models import Area
from src.staff.constants import EffectiveStatus, ManualStatus
from src.staff.models import Staff, staff_area
from src.staff.schemas import (
    ManualStatusUpdate,
    StaffActivo,
    StaffCreate,
    StaffRead,
    StaffUpdate,
)
from src.turnos.constants import ServicioEstado
from src.turnos.models import Cliente, ClientePreseleccion, TurnoServicio


async def _active_by_staff(db: AsyncSession) -> dict[int, list[StaffActivo]]:
    """Servicios en atención o reposo visibles en la carga del especialista."""
    stmt = (
        select(TurnoServicio, Cliente)
        .join(Cliente, Cliente.id == TurnoServicio.cliente_id)
        .where(
            TurnoServicio.estado.in_([ServicioEstado.EN_ATENCION, ServicioEstado.REPOSO]),
            TurnoServicio.staff_numero.is_not(None),
        )
    )
    result = await db.execute(stmt)
    active: dict[int, list[StaffActivo]] = {}
    for sv, cli in result.all():
        active.setdefault(sv.staff_numero, []).append(
            StaffActivo(
                cliente_id=cli.id,
                turno=cli.turno,
                cliente=cli.nombre,
                servicio=sv.nombre,
                estado=sv.estado,
            )
        )
    return active


def _to_read(
    s: Staff,
    active: dict[int, list[StaffActivo]],
    preselection_counts: dict[int, int],
    preselection_by_area: dict[int, dict[str, int]],
) -> StaffRead:
    activos = active.get(s.numero, [])
    atendiendo = any(item.estado == ServicioEstado.EN_ATENCION for item in activos)
    status = EffectiveStatus.OCUPADO if atendiendo else EffectiveStatus(s.manual_status)
    return StaffRead(
        numero=s.numero,
        alias=s.alias,
        nombre=s.nombre,
        cedula=s.cedula,
        initials=s.initials,
        areas=[a.key for a in s.areas],
        manual_status=ManualStatus(s.manual_status),
        en_prueba=s.en_prueba,
        activo=s.activo,
        status=status,
        activos=activos,
        preseleccion_count=preselection_counts.get(s.numero, 0),
        preseleccion_por_area=preselection_by_area.get(s.numero, {}),
    )


async def _preselection_counts(
    db: AsyncSession,
) -> tuple[dict[int, int], dict[int, dict[str, int]]]:
    """Cuenta preferencias aún necesarias, por cliente y por área compatible.

    Una clienta deja de contar para las especialistas de un área cuando todos sus
    servicios de esa área ya tienen especialista. La preferencia original se conserva.
    """
    pending_services = (
        select(
            TurnoServicio.cliente_id.label("cliente_id"),
            TurnoServicio.area_key.label("area_key"),
        )
        .join(Cliente, Cliente.id == TurnoServicio.cliente_id)
        .where(
            Cliente.activo.is_(True),
            TurnoServicio.estado == ServicioEstado.PENDIENTE,
            TurnoServicio.staff_numero.is_(None),
        )
        .distinct()
        .subquery()
    )
    result = await db.execute(
        select(
            ClientePreseleccion.staff_numero,
            ClientePreseleccion.cliente_id,
            pending_services.c.area_key,
        )
        .join(
            pending_services,
            pending_services.c.cliente_id == ClientePreseleccion.cliente_id,
        )
        .join(
            staff_area,
            (staff_area.c.staff_numero == ClientePreseleccion.staff_numero)
            & (staff_area.c.area_key == pending_services.c.area_key),
        )
        .distinct()
    )
    client_ids: dict[int, set[int]] = {}
    area_client_ids: dict[int, dict[str, set[int]]] = {}
    for staff_numero, cliente_id, area_key in result.all():
        client_ids.setdefault(staff_numero, set()).add(cliente_id)
        area_client_ids.setdefault(staff_numero, {}).setdefault(area_key, set()).add(cliente_id)
    return (
        {staff_numero: len(ids) for staff_numero, ids in client_ids.items()},
        {
            staff_numero: {area_key: len(ids) for area_key, ids in areas.items()}
            for staff_numero, areas in area_client_ids.items()
        },
    )


async def get_record_or_404(db: AsyncSession, numero: int) -> Staff:
    stmt = select(Staff).options(selectinload(Staff.areas)).where(Staff.numero == numero)
    result = await db.execute(stmt)
    st = result.scalar_one_or_none()
    if st is None:
        raise NotFound(f"especialista {numero} no existe")
    return st


async def get_or_404(db: AsyncSession, numero: int) -> Staff:
    st = await get_record_or_404(db, numero)
    if not st.activo:
        raise NotFound(f"especialista {numero} no existe o está eliminada")
    return st


async def list_staff(
    db: AsyncSession,
    area: str | None = None,
    status: str | None = None,
    include_inactive: bool = False,
) -> list[StaffRead]:
    stmt = select(Staff).options(selectinload(Staff.areas)).order_by(Staff.numero)
    if not include_inactive:
        stmt = stmt.where(Staff.activo.is_(True))
    result = await db.execute(stmt)
    all_staff = list(result.scalars().all())

    if area is not None:
        all_staff = [s for s in all_staff if any(a.key == area for a in s.areas)]

    active = await _active_by_staff(db)
    preselection_counts, preselection_by_area = await _preselection_counts(db)
    reads = [_to_read(s, active, preselection_counts, preselection_by_area) for s in all_staff]
    if status is not None:
        reads = [r for r in reads if r.status == status]
    return reads


async def set_manual_status(db: AsyncSession, numero: int, data: ManualStatusUpdate) -> StaffRead:
    st = await get_or_404(db, numero)
    st.manual_status = data.manual_status
    await db.commit()
    await db.refresh(st)
    active = await _active_by_staff(db)
    counts, by_area = await _preselection_counts(db)
    return _to_read(st, active, counts, by_area)


async def toggle_en_prueba(db: AsyncSession, numero: int) -> StaffRead:
    st = await get_or_404(db, numero)
    st.en_prueba = not st.en_prueba
    await db.commit()
    await db.refresh(st)
    active = await _active_by_staff(db)
    counts, by_area = await _preselection_counts(db)
    return _to_read(st, active, counts, by_area)


async def get_read_or_404(db: AsyncSession, numero: int) -> StaffRead:
    st = await get_or_404(db, numero)
    active = await _active_by_staff(db)
    counts, by_area = await _preselection_counts(db)
    return _to_read(st, active, counts, by_area)


async def eligible_for(db: AsyncSession, area: str) -> list[StaffRead]:
    """Personal que cubre `area` y cuyo estado efectivo es DISPONIBLE."""
    staff = await list_staff(db, area=area)
    return [s for s in staff if s.status == EffectiveStatus.DISPONIBLE]


async def _get_areas(db: AsyncSession, keys: list[str]) -> list[Area]:
    result = await db.execute(select(Area).where(Area.key.in_(keys), Area.activo.is_(True)))
    areas = list(result.scalars().all())
    missing = set(keys) - {area.key for area in areas}
    if missing:
        raise NotFound(f"áreas no encontradas: {sorted(missing)}")
    return areas


def _initials(nombre: str) -> str:
    return "".join(part[0] for part in nombre.split()[:2]).upper()


async def create_staff(db: AsyncSession, data: StaffCreate) -> StaffRead:
    if await db.get(Staff, data.numero) is not None:
        raise Conflict(f"especialista {data.numero} ya existe")
    staff = Staff(
        numero=data.numero,
        alias=data.alias.strip(),
        nombre=data.nombre.strip(),
        cedula=data.cedula.strip().upper(),
        initials=_initials(data.nombre),
        manual_status=ManualStatus.DISPONIBLE,
        en_prueba=data.en_prueba,
        areas=await _get_areas(db, data.areas),
    )
    db.add(staff)
    await db.commit()
    return await get_read_or_404(db, staff.numero)


async def update_staff(db: AsyncSession, numero: int, data: StaffUpdate) -> StaffRead:
    staff = await get_or_404(db, numero)
    changes = data.model_dump(exclude_unset=True)
    area_keys = changes.pop("areas", None)
    for field, value in changes.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(staff, field, value)
    if "nombre" in changes:
        staff.initials = _initials(staff.nombre)
    if area_keys is not None:
        staff.areas = await _get_areas(db, area_keys)
    await db.commit()
    return await get_read_or_404(db, numero)


async def archive_staff(db: AsyncSession, numero: int) -> None:
    staff = await get_or_404(db, numero)
    active_service = await db.scalar(
        select(TurnoServicio.id)
        .where(
            TurnoServicio.staff_numero == numero,
            TurnoServicio.estado.not_in([ServicioEstado.FINALIZADO, ServicioEstado.CANCELADO]),
        )
        .limit(1)
    )
    if active_service is not None:
        raise Conflict("la especialista tiene servicios activos; termínalos o reasígnalos primero")
    staff.activo = False
    await db.commit()


async def restore_staff(db: AsyncSession, numero: int) -> StaffRead:
    staff = await get_record_or_404(db, numero)
    if staff.activo:
        raise Conflict("la especialista ya está activa")
    inactive_areas = [area.name for area in staff.areas if not area.activo]
    if inactive_areas:
        raise Conflict(
            "restaura primero las áreas de la especialista: " + ", ".join(inactive_areas)
        )
    staff.activo = True
    staff.manual_status = ManualStatus.DISPONIBLE
    await db.commit()
    return await get_read_or_404(db, numero)
