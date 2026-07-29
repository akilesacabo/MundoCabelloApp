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
from src.staff.models import Staff
from src.staff.schemas import (
    ManualStatusUpdate,
    StaffActivo,
    StaffCreate,
    StaffRead,
    StaffUpdate,
)
from src.turnos.constants import ServicioEstado
from src.turnos.models import Cliente, TurnoServicio


async def _active_by_staff(db: AsyncSession) -> dict[int, list[StaffActivo]]:
    """Servicios en atención o reposo visibles en la carga del especialista."""
    stmt = (
        select(TurnoServicio, Cliente)
        .join(Cliente, Cliente.id == TurnoServicio.cliente_id)
        .where(
            TurnoServicio.estado.in_(
                [ServicioEstado.EN_ATENCION, ServicioEstado.REPOSO]
            ),
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


def _to_read(s: Staff, active: dict[int, list[StaffActivo]]) -> StaffRead:
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
        status=status,
        activos=activos,
    )


async def get_or_404(db: AsyncSession, numero: int) -> Staff:
    stmt = select(Staff).options(selectinload(Staff.areas)).where(Staff.numero == numero)
    result = await db.execute(stmt)
    st = result.scalar_one_or_none()
    if st is None:
        raise NotFound(f"especialista {numero} no existe")
    return st


async def list_staff(
    db: AsyncSession,
    area: str | None = None,
    status: str | None = None,
) -> list[StaffRead]:
    stmt = select(Staff).options(selectinload(Staff.areas)).order_by(Staff.numero)
    result = await db.execute(stmt)
    all_staff = list(result.scalars().all())

    if area is not None:
        all_staff = [s for s in all_staff if any(a.key == area for a in s.areas)]

    active = await _active_by_staff(db)
    reads = [_to_read(s, active) for s in all_staff]
    if status is not None:
        reads = [r for r in reads if r.status == status]
    return reads


async def set_manual_status(
    db: AsyncSession, numero: int, data: ManualStatusUpdate
) -> StaffRead:
    st = await get_or_404(db, numero)
    st.manual_status = data.manual_status
    await db.commit()
    await db.refresh(st)
    active = await _active_by_staff(db)
    return _to_read(st, active)


async def toggle_en_prueba(db: AsyncSession, numero: int) -> StaffRead:
    st = await get_or_404(db, numero)
    st.en_prueba = not st.en_prueba
    await db.commit()
    await db.refresh(st)
    active = await _active_by_staff(db)
    return _to_read(st, active)


async def get_read_or_404(db: AsyncSession, numero: int) -> StaffRead:
    st = await get_or_404(db, numero)
    active = await _active_by_staff(db)
    return _to_read(st, active)


async def eligible_for(db: AsyncSession, area: str) -> list[StaffRead]:
    """Personal que cubre `area` y cuyo estado efectivo es DISPONIBLE."""
    staff = await list_staff(db, area=area)
    return [s for s in staff if s.status == EffectiveStatus.DISPONIBLE]


async def _get_areas(db: AsyncSession, keys: list[str]) -> list[Area]:
    result = await db.execute(select(Area).where(Area.key.in_(keys)))
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
