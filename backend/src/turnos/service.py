"""Lógica de turnos: check-in, asignación por servicio, finalización, cambio
de especialista con PIN. Espeja `mockups/v2/store.js`.
"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import settings
from src.exceptions import BadRequest, Conflict, NotFound, PermissionDenied
from src.historial.models import Historial
from src.services import service as services_service
from src.staff import service as staff_service
from src.staff.constants import ManualStatus
from src.staff.models import Staff
from src.turnos.constants import ServicioEstado, SituacionTurno, TurnoEstado
from src.turnos.models import (
    Cliente,
    ClienteEtiqueta,
    ClienteProfile,
    ServicioCambio,
    TurnoServicio,
)
from src.turnos.schemas import (
    AssignManyRequest,
    AssignRequest,
    ChangeSpecialistRequest,
    CheckInRequest,
    ClienteProfileRead,
    ClienteProfileSummary,
    ClienteRead,
    PublicQueueRead,
    SituacionUpdate,
    TurnoDetailsUpdate,
    TurnoServicioRead,
)


def _turno_estado(c: Cliente) -> TurnoEstado:
    if c.servicios and all(sv.estado == ServicioEstado.FINALIZADO for sv in c.servicios):
        return TurnoEstado.FINALIZADO
    if any(sv.estado != ServicioEstado.PENDIENTE for sv in c.servicios):
        return TurnoEstado.EN_ATENCION
    return TurnoEstado.EN_ESPERA


def _to_read(c: Cliente) -> ClienteRead:
    return ClienteRead(
        id=c.id,
        turno=c.turno,
        cedula=c.cedula,
        nombre=c.nombre,
        telefono=c.telefono,
        direccion=c.direccion,
        observacion=c.observacion,
        etiquetas=sorted(tag.codigo for tag in c.etiquetas),
        situacion=c.situacion,
        activo=c.activo,
        created_at=c.created_at,
        estado=_turno_estado(c),
        servicios=[TurnoServicioRead.model_validate(sv) for sv in c.servicios],
    )


async def _load_cliente(db: AsyncSession, cliente_id: int) -> Cliente:
    stmt = (
        select(Cliente)
        .options(
            selectinload(Cliente.servicios).selectinload(TurnoServicio.cambios),
            selectinload(Cliente.etiquetas),
        )
        .where(Cliente.id == cliente_id)
    )
    result = await db.execute(stmt)
    c = result.scalar_one_or_none()
    if c is None:
        raise NotFound(f"turno {cliente_id} no existe")
    return c


async def _next_turno(db: AsyncSession) -> int:
    """Número siguiente, preservando el inicio #13 de la demo."""
    ultimo = await db.scalar(select(func.max(Cliente.turno)))
    return max(13, int(ultimo or 12) + 1)


def normalize_cedula(value: str) -> str:
    compact = "".join(char for char in value.strip().upper() if char.isalnum())
    if compact[:1] in {"V", "E"}:
        return f"{compact[0]}-{compact[1:]}"
    return compact


async def _active_for_cedula(
    db: AsyncSession, cedula: str, *, exclude_id: int | None = None
) -> Cliente | None:
    stmt = select(Cliente).where(Cliente.cedula == cedula, Cliente.activo.is_(True))
    if exclude_id is not None:
        stmt = stmt.where(Cliente.id != exclude_id)
    return (await db.execute(stmt.order_by(Cliente.created_at.desc()))).scalars().first()


async def _upsert_profile(
    db: AsyncSession, payload: CheckInRequest, cedula: str
) -> ClienteProfile:
    profile = (
        await db.execute(select(ClienteProfile).where(ClienteProfile.cedula == cedula))
    ).scalar_one_or_none()
    if profile is None:
        profile = ClienteProfile(
            cedula=cedula,
            nombre=payload.nombre.strip(),
            telefono=payload.telefono.strip(),
            direccion=payload.direccion.strip(),
        )
        db.add(profile)
        await db.flush()
    else:
        profile.nombre = payload.nombre.strip()
        profile.telefono = payload.telefono.strip()
        profile.direccion = payload.direccion.strip()
    return profile


async def check_in(db: AsyncSession, payload: CheckInRequest) -> ClienteRead:
    cedula = normalize_cedula(payload.cedula)
    active = await _active_for_cedula(db, cedula)
    if active is not None:
        raise Conflict(
            f"El cliente ya tiene el turno activo #{active.turno}. "
            "Actualiza ese turno en lugar de registrarlo nuevamente."
        )
    catalog = await services_service.get_many_or_404(db, payload.service_ids)
    profile = await _upsert_profile(db, payload, cedula)
    turno = await _next_turno(db)
    cliente = Cliente(
        turno=turno,
        perfil_id=profile.id,
        cedula=cedula,
        nombre=payload.nombre.strip(),
        telefono=payload.telefono.strip(),
        direccion=payload.direccion.strip(),
        observacion=payload.observacion.strip(),
        situacion=SituacionTurno.PRESENTE,
        activo=True,
        etiquetas=[ClienteEtiqueta(codigo=tag.value) for tag in payload.etiquetas],
        servicios=[
            TurnoServicio(
                area_key=s.area_key,
                nombre=s.nombre,
                precio_usd=s.precio_usd,
                estado=ServicioEstado.PENDIENTE,
            )
            for s in catalog
        ],
    )
    db.add(cliente)
    await db.commit()
    return _to_read(await _load_cliente(db, cliente.id))


async def list_clientes(db: AsyncSession, estado: str | None = None) -> list[ClienteRead]:
    stmt = (
        select(Cliente)
        .options(
            selectinload(Cliente.servicios).selectinload(TurnoServicio.cambios),
            selectinload(Cliente.etiquetas),
        )
        .order_by(Cliente.created_at)
    )
    result = await db.execute(stmt)
    all_c = [_to_read(c) for c in result.scalars().all()]
    if estado is not None:
        all_c = [c for c in all_c if c.estado == estado]
    return all_c


async def get_cliente(db: AsyncSession, cliente_id: int) -> ClienteRead:
    return _to_read(await _load_cliente(db, cliente_id))


async def _get_servicio(
    db: AsyncSession, cliente_id: int, servicio_id: int
) -> tuple[Cliente, TurnoServicio]:
    c = await _load_cliente(db, cliente_id)
    sv = next((s for s in c.servicios if s.id == servicio_id), None)
    if sv is None:
        raise NotFound(f"servicio {servicio_id} no pertenece al turno {cliente_id}")
    return c, sv


async def find_profile(db: AsyncSession, cedula: str) -> ClienteProfileRead:
    normalized = normalize_cedula(cedula)
    profile = (
        await db.execute(
            select(ClienteProfile).where(ClienteProfile.cedula == normalized)
        )
    ).scalar_one_or_none()
    if profile is None:
        raise NotFound("cliente no encontrado")
    return ClienteProfileRead.model_validate(profile, from_attributes=True)


async def search_profiles(db: AsyncSession, query: str) -> list[ClienteProfileRead]:
    term = query.strip().upper()
    compact = "".join(char for char in term if char.isalnum())
    patterns = [f"%{term}%"]
    if compact:
        patterns.extend([f"%{compact}%", f"%{compact[:1]}-{compact[1:]}%"])
    stmt = (
        select(ClienteProfile)
        .where(
            or_(
                ClienteProfile.cedula.ilike(patterns[0]),
                ClienteProfile.cedula.ilike(patterns[-1]),
            )
        )
        .order_by(ClienteProfile.nombre)
        .limit(8)
    )
    profiles = (await db.execute(stmt)).scalars().all()
    return [
        ClienteProfileRead.model_validate(profile, from_attributes=True)
        for profile in profiles
    ]


async def list_profiles(db: AsyncSession) -> list[ClienteProfileSummary]:
    profiles = (
        await db.execute(select(ClienteProfile).order_by(ClienteProfile.nombre))
    ).scalars().all()
    rows: list[ClienteProfileSummary] = []
    for profile in profiles:
        stmt = (
            select(Cliente)
            .options(selectinload(Cliente.etiquetas))
            .where(Cliente.perfil_id == profile.id)
            .order_by(Cliente.created_at.desc())
        )
        visits = list((await db.execute(stmt)).scalars().all())
        rows.append(
            ClienteProfileSummary(
                id=profile.id,
                cedula=profile.cedula,
                nombre=profile.nombre,
                telefono=profile.telefono,
                direccion=profile.direccion,
                visitas=len(visits),
                ultima_visita=visits[0].created_at if visits else None,
                etiquetas=[tag.codigo for tag in visits[0].etiquetas] if visits else [],
            )
        )
    return rows


async def update_details(
    db: AsyncSession, cliente_id: int, payload: TurnoDetailsUpdate
) -> ClienteRead:
    cliente = await _load_cliente(db, cliente_id)
    cliente.observacion = payload.observacion.strip()
    cliente.etiquetas = [
        ClienteEtiqueta(codigo=tag.value) for tag in payload.etiquetas
    ]
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def update_situacion(
    db: AsyncSession, cliente_id: int, payload: SituacionUpdate
) -> ClienteRead:
    cliente = await _load_cliente(db, cliente_id)
    cliente.situacion = payload.situacion
    if payload.situacion == SituacionTurno.ESTAFA:
        cliente.activo = False
    elif payload.situacion == SituacionTurno.PRESENTE:
        duplicate = await _active_for_cedula(
            db, cliente.cedula, exclude_id=cliente.id
        )
        if duplicate is not None:
            raise Conflict(f"La cédula ya tiene el turno activo #{duplicate.turno}.")
        cliente.activo = _turno_estado(cliente) != TurnoEstado.FINALIZADO
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def public_queue(db: AsyncSession) -> PublicQueueRead:
    clientes = await list_clientes(db)
    visibles = [c for c in clientes if c.situacion == SituacionTurno.PRESENTE]
    atendiendo = [c.turno for c in visibles if c.estado == TurnoEstado.EN_ATENCION]
    en_espera = [c.turno for c in visibles if c.estado == TurnoEstado.EN_ESPERA]
    ultimo = max((c.created_at for c in visibles), default=None)
    return PublicQueueRead(
        atendiendo=atendiendo, en_espera=en_espera, ultimo_cambio=ultimo
    )


async def assigned_to_staff(db: AsyncSession, staff_numero: int) -> list[ClienteRead]:
    clientes = await list_clientes(db)
    return [
        c
        for c in clientes
        if any(
            sv.staff_numero == staff_numero and sv.estado != ServicioEstado.FINALIZADO
            for sv in c.servicios
        )
    ]


async def _validate_staff_for_area(db: AsyncSession, staff_numero: int, area_key: str) -> Staff:
    st = await staff_service.get_or_404(db, staff_numero)
    if st.manual_status != ManualStatus.DISPONIBLE:
        raise BadRequest(
            f"el especialista {st.alias} no está disponible para nuevas asignaciones"
        )
    if not any(a.key == area_key for a in st.areas):
        raise BadRequest(
            f"el especialista {st.alias} no cubre el área {area_key!r}"
        )
    return st


async def assign_service(
    db: AsyncSession, cliente_id: int, servicio_id: int, payload: AssignRequest
) -> ClienteRead:
    c, sv = await _get_servicio(db, cliente_id, servicio_id)
    if sv.estado == ServicioEstado.FINALIZADO:
        raise BadRequest("no se puede reasignar un servicio ya finalizado")
    await _validate_staff_for_area(db, payload.staff_numero, sv.area_key)
    sv.staff_numero = payload.staff_numero
    sv.estado = ServicioEstado.EN_ATENCION
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def assign_many(
    db: AsyncSession, cliente_id: int, payload: AssignManyRequest
) -> ClienteRead:
    c = await _load_cliente(db, cliente_id)
    target = {sv.id: sv for sv in c.servicios if sv.id in payload.servicio_ids}
    missing = set(payload.servicio_ids) - target.keys()
    if missing:
        raise NotFound(f"servicios no encontrados en el turno: {sorted(missing)}")

    st = await staff_service.get_or_404(db, payload.staff_numero)
    if st.manual_status != ManualStatus.DISPONIBLE:
        raise BadRequest(
            f"el especialista {st.alias} no está disponible para nuevas asignaciones"
        )
    staff_areas = {a.key for a in st.areas}
    for sv in target.values():
        if sv.estado == ServicioEstado.FINALIZADO:
            raise BadRequest(f"servicio {sv.id} ya está finalizado")
        if sv.area_key not in staff_areas:
            raise BadRequest(
                f"el especialista {st.alias} no cubre el área {sv.area_key!r} "
                f"del servicio {sv.nombre!r}"
            )
    for sv in target.values():
        sv.staff_numero = payload.staff_numero
        sv.estado = ServicioEstado.EN_ATENCION
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def finish_service(
    db: AsyncSession, cliente_id: int, servicio_id: int
) -> ClienteRead:
    c, sv = await _get_servicio(db, cliente_id, servicio_id)
    if sv.estado != ServicioEstado.EN_ATENCION:
        raise BadRequest(
            f"solo se finaliza un servicio EN_ATENCION (estado actual: {sv.estado})"
        )
    if sv.staff_numero is None:
        raise BadRequest("el servicio no tiene especialista asignado")

    staff = await staff_service.get_or_404(db, sv.staff_numero)
    sv.estado = ServicioEstado.FINALIZADO
    db.add(
        Historial(
            cliente_id=c.id,
            cliente_nombre=c.nombre,
            cliente_cedula=c.cedula,
            servicio_nombre=sv.nombre,
            area_key=sv.area_key,
            precio_usd=sv.precio_usd,
            staff_numero=staff.numero,
            staff_nombre=staff.alias,
        )
    )
    if all(item.estado == ServicioEstado.FINALIZADO for item in c.servicios):
        c.activo = False
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def change_specialist(
    db: AsyncSession,
    cliente_id: int,
    servicio_id: int,
    payload: ChangeSpecialistRequest,
) -> ClienteRead:
    if payload.pin.strip() != settings.admin_pin:
        raise PermissionDenied("PIN de administrador inválido.")
    if not payload.motivo.strip():
        raise BadRequest("El motivo del cambio es obligatorio.")

    c, sv = await _get_servicio(db, cliente_id, servicio_id)
    if sv.estado == ServicioEstado.FINALIZADO:
        raise BadRequest("no se puede cambiar el especialista de un servicio finalizado")
    await _validate_staff_for_area(db, payload.staff_numero, sv.area_key)

    sv.cambios.append(
        ServicioCambio(
            de_staff=sv.staff_numero,
            a_staff=payload.staff_numero,
            motivo=payload.motivo.strip(),
        )
    )
    sv.staff_numero = payload.staff_numero
    sv.estado = ServicioEstado.EN_ATENCION
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))
