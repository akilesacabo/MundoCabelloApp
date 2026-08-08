"""Lógica de turnos: check-in, asignación por servicio y operación de visitas.
"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.schemas import AuthUser
from src.exceptions import BadRequest, Conflict, NotFound
from src.historial.models import Historial
from src.services import service as services_service
from src.staff import service as staff_service
from src.staff.constants import EffectiveStatus, ManualStatus
from src.staff.models import Staff
from src.turnos.constants import EtiquetaCodigo, ServicioEstado, SituacionTurno, TurnoEstado
from src.turnos.models import (
    Cliente,
    ClienteEtiqueta,
    ClientePreseleccion,
    ClienteProfile,
    ServicioCambio,
    TurnoServicio,
)
from src.turnos.schemas import (
    AreaQueueItemRead,
    AreaQueueRead,
    AssignManyRequest,
    AssignRequest,
    ChangeSpecialistRequest,
    CheckInRequest,
    ClienteHistoryServiceRead,
    ClienteHistoryVisitRead,
    ClienteProfileDetail,
    ClienteProfileRead,
    ClienteProfileSummary,
    ClienteRead,
    PublicQueueClientRead,
    PublicQueueRead,
    ServiceReplaceRequest,
    SituacionUpdate,
    StaffPreferencesUpdate,
    TurnoDetailsUpdate,
    TurnoServicioRead,
)


def _turno_estado(c: Cliente) -> TurnoEstado:
    terminal = {ServicioEstado.FINALIZADO, ServicioEstado.CANCELADO}
    if c.servicios and all(sv.estado in terminal for sv in c.servicios):
        return TurnoEstado.FINALIZADO
    if any(sv.estado == ServicioEstado.EN_ATENCION for sv in c.servicios):
        return TurnoEstado.EN_ATENCION
    if any(sv.estado == ServicioEstado.REPOSO for sv in c.servicios):
        return TurnoEstado.REPOSO
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
        registrado_por_role=c.registrado_por_role,
        registrado_por_subject=c.registrado_por_subject,
        registrado_por_nombre=c.registrado_por_nombre,
        actualizado_por_nombre=c.actualizado_por_nombre,
        preseleccion_staff_numeros=[item.staff_numero for item in c.preselecciones],
        acepta_otro_estilista=c.acepta_otro_estilista,
        created_at=c.created_at,
        estado=_turno_estado(c),
        servicios=[
            TurnoServicioRead.model_validate(sv)
            for sv in c.servicios
            if sv.estado != ServicioEstado.CANCELADO
        ],
    )


def _active_visit(profile: ClienteProfile) -> Cliente | None:
    return next(
        (
            visit
            for visit in sorted(
                profile.turnos,
                key=lambda item: (item.created_at, item.id),
                reverse=True,
            )
            if visit.activo
        ),
        None,
    )


def _profile_to_read(profile: ClienteProfile) -> ClienteProfileRead:
    active = _active_visit(profile)
    return ClienteProfileRead(
        id=profile.id,
        cedula=profile.cedula,
        nombre=profile.nombre,
        telefono=profile.telefono,
        direccion=profile.direccion,
        active_turno_id=active.id if active else None,
        active_turno=active.turno if active else None,
        alerta_estafa=any(
            visit.situacion == SituacionTurno.ESTAFA for visit in profile.turnos
        ),
    )


def _sync_tags(cliente: Cliente, desired: list[str]) -> None:
    desired_codes = set(desired)
    current = {tag.codigo: tag for tag in cliente.etiquetas}
    cliente.etiquetas[:] = [
        tag for code, tag in current.items() if code in desired_codes
    ]
    cliente.etiquetas.extend(
        ClienteEtiqueta(codigo=code)
        for code in sorted(desired_codes - current.keys())
    )


def _sync_solo_unas(cliente: Cliente) -> None:
    """Mantiene la etiqueta automática solo mientras la visita sea exclusivamente manicure."""
    visibles = [sv for sv in cliente.servicios if sv.estado != ServicioEstado.CANCELADO]
    desired = {tag.codigo for tag in cliente.etiquetas if tag.codigo != EtiquetaCodigo.SOLO_UNAS}
    if visibles and all(sv.area_key == "manicure" for sv in visibles):
        desired.add(EtiquetaCodigo.SOLO_UNAS)
    _sync_tags(cliente, sorted(desired))


def _actor_fields(user: AuthUser | None) -> dict[str, str | None]:
    return {
        "role": user.role if user else None,
        "subject": user.subject if user else None,
        "nombre": user.display_name if user else None,
    }


async def _load_cliente(db: AsyncSession, cliente_id: int) -> Cliente:
    stmt = (
        select(Cliente)
        .options(
            selectinload(Cliente.servicios).selectinload(TurnoServicio.cambios),
            selectinload(Cliente.etiquetas),
            selectinload(Cliente.preselecciones),
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
    return (
        await db.execute(stmt.order_by(Cliente.created_at.desc(), Cliente.id.desc()))
    ).scalars().first()


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


async def _apply_staff_preferences(
    db: AsyncSession,
    cliente: Cliente,
    staff_numeros: list[int],
    acepta_otro_estilista: bool,
) -> None:
    """Valida y persiste las preselecciones de una visita."""
    numbers = list(dict.fromkeys(staff_numeros))
    if len(numbers) != len(staff_numeros):
        raise BadRequest("no se puede repetir un especialista en las preferencias")
    if numbers:
        result = await db.execute(select(Staff.numero).where(Staff.numero.in_(numbers)))
        if {row[0] for row in result.all()} != set(numbers):
            raise NotFound("uno o más especialistas no existen")
    cliente.preselecciones.clear()
    # Fuerza las eliminaciones antes de insertar los mismos números nuevamente.
    # La tabla prohíbe repetir (cliente_id, staff_numero).
    await db.flush()
    cliente.preselecciones.extend(
        ClientePreseleccion(staff_numero=numero) for numero in numbers
    )
    cliente.acepta_otro_estilista = acepta_otro_estilista


async def _services_for_checkin(
    db: AsyncSession, payload: CheckInRequest
) -> list[TurnoServicio]:
    catalog = await services_service.get_many_or_404(db, payload.service_ids)
    selected = [
        TurnoServicio(
            area_key=service.area_key,
            nombre=service.nombre,
            precio_usd=service.precio_usd,
            estado=ServicioEstado.PENDIENTE,
        )
        for service in catalog
    ]
    for promotion in await services_service.get_promotion_components_or_404(
        db, payload.promotion_ids
    ):
        selected.extend(
            TurnoServicio(
                area_key=item.servicio.area_key,
                nombre=item.servicio.nombre,
                precio_usd=item.precio_usd,
                estado=ServicioEstado.PENDIENTE,
            )
            for item in promotion.servicios
        )
    return selected


async def check_in(
    db: AsyncSession, payload: CheckInRequest, registered_by: AuthUser | None = None
) -> ClienteRead:
    cedula = normalize_cedula(payload.cedula)
    active = await _active_for_cedula(db, cedula)
    services = await _services_for_checkin(db, payload)
    if active is not None:
        if payload.active_turno_id != active.id:
            raise Conflict(
                f"El cliente ya tiene el turno activo #{active.turno}. "
                "Selecciónalo en la búsqueda para agregar los servicios a esa visita."
            )
        active = await _load_cliente(db, active.id)
        active.servicios.extend(services)
        if payload.observacion.strip():
            active.observacion = payload.observacion.strip()
        merged_tags = {tag.codigo for tag in active.etiquetas}
        merged_tags.update(tag.value for tag in payload.etiquetas)
        _sync_tags(active, sorted(merged_tags))
        _sync_solo_unas(active)
        if payload.staff_numeros_preseleccion or payload.acepta_otro_estilista:
            await _apply_staff_preferences(
                db,
                active,
                payload.staff_numeros_preseleccion,
                payload.acepta_otro_estilista,
            )
        await _upsert_profile(db, payload, cedula)
        await db.commit()
        return _to_read(await _load_cliente(db, active.id))

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
        registrado_por_role=registered_by.role if registered_by else None,
        registrado_por_subject=registered_by.subject if registered_by else None,
        registrado_por_nombre=(
            registered_by.display_name if registered_by else "Autoservicio"
        ),
        etiquetas=[ClienteEtiqueta(codigo=tag.value) for tag in payload.etiquetas],
        preselecciones=[
            ClientePreseleccion(staff_numero=numero)
            for numero in payload.staff_numeros_preseleccion
        ],
        acepta_otro_estilista=payload.acepta_otro_estilista,
        servicios=services,
    )
    db.add(cliente)
    # Validamos aquí las preferencias de un turno nuevo antes de guardar.
    numbers = list(dict.fromkeys(payload.staff_numeros_preseleccion))
    if len(numbers) != len(payload.staff_numeros_preseleccion):
        raise BadRequest("no se puede repetir un especialista en las preferencias")
    if numbers:
        result = await db.execute(select(Staff.numero).where(Staff.numero.in_(numbers)))
        if {row[0] for row in result.all()} != set(numbers):
            raise NotFound("uno o más especialistas no existen")
    _sync_solo_unas(cliente)
    await db.commit()
    return _to_read(await _load_cliente(db, cliente.id))


async def list_clientes(db: AsyncSession, estado: str | None = None) -> list[ClienteRead]:
    stmt = (
        select(Cliente)
        .options(
            selectinload(Cliente.servicios).selectinload(TurnoServicio.cambios),
            selectinload(Cliente.etiquetas),
            selectinload(Cliente.preselecciones),
        )
        .order_by(Cliente.created_at)
    )
    result = await db.execute(stmt)
    all_c = [_to_read(c) for c in result.scalars().all()]
    all_c.sort(
        key=lambda client: (
            "INT" not in client.etiquetas,
            client.nombre.casefold(),
            client.created_at,
            client.id,
        )
    )
    if estado is not None:
        all_c = [c for c in all_c if c.estado == estado]
    area_pending_clients: dict[str, set[int]] = {}
    for client in all_c:
        if not client.activo or client.situacion != SituacionTurno.PRESENTE:
            continue
        for service in client.servicios:
            if service.estado == ServicioEstado.PENDIENTE and service.staff_numero is None:
                area_pending_clients.setdefault(service.area_key, set()).add(client.id)
    area_counts = {
        area: len(client_ids) for area, client_ids in area_pending_clients.items()
    }
    for client in all_c:
        for service in client.servicios:
            service.pendientes_area = area_counts.get(service.area_key, 0)
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
            select(ClienteProfile)
            .options(selectinload(ClienteProfile.turnos))
            .where(ClienteProfile.cedula == normalized)
        )
    ).scalar_one_or_none()
    if profile is None:
        raise NotFound("cliente no encontrado")
    return _profile_to_read(profile)


async def search_profiles(db: AsyncSession, query: str) -> list[ClienteProfileRead]:
    term = query.strip().upper()
    compact = "".join(char for char in term if char.isalnum())
    patterns = [f"%{term}%"]
    if compact:
        patterns.extend([f"%{compact}%", f"%{compact[:1]}-{compact[1:]}%"])
    stmt = (
        select(ClienteProfile)
        .options(selectinload(ClienteProfile.turnos))
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
    return [_profile_to_read(profile) for profile in profiles]


async def list_profiles(db: AsyncSession) -> list[ClienteProfileSummary]:
    profiles = (
        await db.execute(
            select(ClienteProfile)
            .options(
                selectinload(ClienteProfile.turnos).selectinload(Cliente.etiquetas)
            )
            .order_by(ClienteProfile.nombre)
        )
    ).scalars().all()
    rows: list[ClienteProfileSummary] = []
    for profile in profiles:
        visits = sorted(
            profile.turnos,
            key=lambda visit: (visit.created_at, visit.id),
            reverse=True,
        )
        active = _active_visit(profile)
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
                active_turno_id=active.id if active else None,
                active_turno=active.turno if active else None,
            )
        )
    return rows


async def get_profile_detail(
    db: AsyncSession, profile_id: int
) -> ClienteProfileDetail:
    stmt = (
        select(ClienteProfile)
        .options(
            selectinload(ClienteProfile.turnos)
            .selectinload(Cliente.servicios)
            .selectinload(TurnoServicio.staff),
            selectinload(ClienteProfile.turnos).selectinload(Cliente.etiquetas),
        )
        .where(ClienteProfile.id == profile_id)
    )
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if profile is None:
        raise NotFound(f"perfil de cliente {profile_id} no existe")

    visits = sorted(
        profile.turnos,
        key=lambda visit: (visit.created_at, visit.id),
        reverse=True,
    )
    return ClienteProfileDetail(
        id=profile.id,
        cedula=profile.cedula,
        nombre=profile.nombre,
        telefono=profile.telefono,
        direccion=profile.direccion,
        visitas=[
            ClienteHistoryVisitRead(
                id=visit.id,
                turno=visit.turno,
                created_at=visit.created_at,
                observacion=visit.observacion,
                etiquetas=sorted(tag.codigo for tag in visit.etiquetas),
                situacion=visit.situacion,
                activo=visit.activo,
                registrado_por_nombre=visit.registrado_por_nombre,
                estado=_turno_estado(visit),
                servicios=[
                    ClienteHistoryServiceRead(
                        id=service.id,
                        area_key=service.area_key,
                        nombre=service.nombre,
                        precio_usd=service.precio_usd,
                        staff_numero=service.staff_numero,
                        especialista=service.staff.alias if service.staff else None,
                        estado=service.estado,
                    )
                    for service in visit.servicios
                ],
            )
            for visit in visits
        ],
    )


async def update_details(
    db: AsyncSession,
    cliente_id: int,
    payload: TurnoDetailsUpdate,
    updated_by: AuthUser | None = None,
) -> ClienteRead:
    cliente = await _load_cliente(db, cliente_id)
    cliente.observacion = payload.observacion.strip()
    _sync_tags(cliente, [tag.value for tag in payload.etiquetas])
    _sync_solo_unas(cliente)
    actor = _actor_fields(updated_by)
    cliente.actualizado_por_role = actor["role"]
    cliente.actualizado_por_subject = actor["subject"]
    cliente.actualizado_por_nombre = actor["nombre"]
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def update_situacion(
    db: AsyncSession,
    cliente_id: int,
    payload: SituacionUpdate,
    updated_by: AuthUser | None = None,
) -> ClienteRead:
    cliente = await _load_cliente(db, cliente_id)
    cliente.situacion = payload.situacion
    actor = _actor_fields(updated_by)
    cliente.actualizado_por_role = actor["role"]
    cliente.actualizado_por_subject = actor["subject"]
    cliente.actualizado_por_nombre = actor["nombre"]
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
    visibles = [
        c for c in clientes if c.activo and c.situacion == SituacionTurno.PRESENTE
    ]
    atendiendo = [
        PublicQueueClientRead(turno=c.turno, nombre=c.nombre)
        for c in visibles
        if c.estado == TurnoEstado.EN_ATENCION
    ]
    en_reposo = [
        PublicQueueClientRead(turno=c.turno, nombre=c.nombre)
        for c in visibles
        if c.estado == TurnoEstado.REPOSO
    ]
    en_espera = [
        PublicQueueClientRead(turno=c.turno, nombre=c.nombre)
        for c in visibles
        if c.estado == TurnoEstado.EN_ESPERA
    ]
    ultimo = max((c.created_at for c in visibles), default=None)
    area_queues = _area_queues(visibles)
    return PublicQueueRead(
        atendiendo=atendiendo,
        en_reposo=en_reposo,
        en_espera=en_espera,
        ultimo_cambio=ultimo,
        por_area=area_queues,
    )


def _area_queues(clientes: list[ClienteRead]) -> list[AreaQueueRead]:
    area_buckets: dict[str, dict[str, list[AreaQueueItemRead]]] = {}
    waiting_seen: dict[str, int] = {}
    for client in clientes:
        for service in client.servicios:
            if service.estado == ServicioEstado.FINALIZADO:
                continue
            bucket = area_buckets.setdefault(
                service.area_key,
                {"atendiendo": [], "en_reposo": [], "en_espera": []},
            )
            waiting_index: int | None = None
            people_ahead = 0
            if service.estado == ServicioEstado.PENDIENTE and service.staff_numero is None:
                waiting_index = waiting_seen.get(service.area_key, 0) + 1
                waiting_seen[service.area_key] = waiting_index
                people_ahead = waiting_index - 1
                target = "en_espera"
            elif service.estado == ServicioEstado.REPOSO:
                target = "en_reposo"
            elif service.estado == ServicioEstado.EN_ATENCION:
                target = "atendiendo"
            else:
                target = "en_espera"
            bucket[target].append(
                AreaQueueItemRead(
                    cliente_id=client.id,
                    servicio_id=service.id,
                    turno=client.turno,
                    cliente_nombre=client.nombre,
                    servicio_nombre=service.nombre,
                    estado=service.estado,
                    posicion=waiting_index,
                    personas_delante=people_ahead,
                )
            )
    return [
        AreaQueueRead(
            area_key=area_key,
            atendiendo=buckets["atendiendo"],
            en_reposo=buckets["en_reposo"],
            en_espera=buckets["en_espera"],
        )
        for area_key, buckets in sorted(area_buckets.items())
    ]


async def queue_positions(db: AsyncSession, query: str) -> list[dict]:
    """Busca clientes activos y calcula su posición sobre la espera efectiva."""
    clientes = [
        client
        for client in await list_clientes(db)
        if client.activo and client.situacion == SituacionTurno.PRESENTE
    ]
    waiting = [client for client in clientes if client.estado == TurnoEstado.EN_ESPERA]
    positions = {client.id: index + 1 for index, client in enumerate(waiting)}
    area_positions = _service_area_positions(clientes)
    term = query.strip().casefold()
    digits = "".join(char for char in term if char.isdigit())
    matches = [
        client
        for client in clientes
        if term in client.nombre.casefold()
        or term in client.cedula.casefold()
        or (digits and str(client.turno) == digits)
    ][:10]
    return [
        {
            "id": client.id,
            "turno": client.turno,
            "nombre": client.nombre,
            "estado": client.estado,
            "prioridad_int": "INT" in client.etiquetas,
            "posicion": positions.get(client.id),
            "personas_delante": max(0, positions.get(client.id, 1) - 1),
            "areas": [
                area_positions[service.id]
                for service in client.servicios
                if service.id in area_positions
            ],
        }
        for client in matches
    ]


def _service_area_positions(clientes: list[ClienteRead]) -> dict[int, dict]:
    positions: dict[int, dict] = {}
    waiting_seen: dict[str, int] = {}
    for client in clientes:
        for service in client.servicios:
            if service.estado == ServicioEstado.FINALIZADO:
                continue
            position: int | None = None
            people_ahead = 0
            if service.estado == ServicioEstado.PENDIENTE and service.staff_numero is None:
                position = waiting_seen.get(service.area_key, 0) + 1
                waiting_seen[service.area_key] = position
                people_ahead = position - 1
            positions[service.id] = {
                "area_key": service.area_key,
                "servicio_id": service.id,
                "servicio_nombre": service.nombre,
                "estado": service.estado,
                "posicion": position,
                "personas_delante": people_ahead,
            }
    return positions


async def assigned_to_staff(db: AsyncSession, staff_numero: int) -> list[ClienteRead]:
    clientes = await list_clientes(db)
    assigned: list[ClienteRead] = []
    for client in clientes:
        own_services = [
            service
            for service in client.servicios
            if service.staff_numero == staff_numero
            and service.estado != ServicioEstado.FINALIZADO
        ]
        if own_services:
            assigned.append(client.model_copy(update={"servicios": own_services}))
    return assigned


async def _validate_staff_for_area(
    db: AsyncSession,
    staff_numero: int,
    area_key: str,
    *,
    confirmar_ocupado: bool = False,
    cliente_id: int | None = None,
) -> Staff:
    st = await staff_service.get_or_404(db, staff_numero)
    effective = await staff_service.get_read_or_404(db, staff_numero)
    if not any(a.key == area_key for a in st.areas):
        raise BadRequest(
            f"el especialista {st.alias} no cubre el área {area_key!r}"
        )
    if effective.status in {EffectiveStatus.BREAK, EffectiveStatus.ALMORZANDO}:
        raise BadRequest(
            f"el especialista {st.alias} no está disponible para nuevas asignaciones"
        )
    atendiendo_este_cliente = any(
        item.estado == ServicioEstado.EN_ATENCION and item.cliente_id == cliente_id
        for item in effective.activos
    )
    atendiendo_otro_cliente = any(
        item.estado == ServicioEstado.EN_ATENCION and item.cliente_id != cliente_id
        for item in effective.activos
    )
    requiere_confirmacion = effective.status == EffectiveStatus.OCUPADO and (
        atendiendo_otro_cliente or not atendiendo_este_cliente
    )
    if requiere_confirmacion and not confirmar_ocupado:
        carga = ", ".join(f"#{item.turno} · {item.cliente}" for item in effective.activos)
        detalle = f"el especialista {st.alias} está ocupado"
        if carga:
            detalle += f" ({carga})"
        raise Conflict(detalle + ". Confirma la asignación para continuar.")
    return st


async def assign_service(
    db: AsyncSession,
    cliente_id: int,
    servicio_id: int,
    payload: AssignRequest,
    assigned_by: AuthUser | None = None,
) -> ClienteRead:
    c, sv = await _get_servicio(db, cliente_id, servicio_id)
    if sv.estado in {ServicioEstado.FINALIZADO, ServicioEstado.CANCELADO}:
        raise BadRequest("no se puede reasignar un servicio ya finalizado")
    await _validate_staff_for_area(
        db,
        payload.staff_numero,
        sv.area_key,
        confirmar_ocupado=payload.confirmar_ocupado,
        cliente_id=cliente_id,
    )
    actor = _actor_fields(assigned_by)
    previous_staff_numero = sv.staff_numero
    if previous_staff_numero is not None and previous_staff_numero != payload.staff_numero:
        sv.cambios.append(
            ServicioCambio(
                de_staff=previous_staff_numero,
                a_staff=payload.staff_numero,
                motivo="Cambio de especialista durante asignación",
                cambiado_por_role=actor["role"],
                cambiado_por_subject=actor["subject"],
                cambiado_por_nombre=actor["nombre"],
            )
        )
    sv.staff_numero = payload.staff_numero
    sv.estado = ServicioEstado.EN_ATENCION
    sv.asignado_por_role = actor["role"]
    sv.asignado_por_subject = actor["subject"]
    sv.asignado_por_nombre = actor["nombre"]
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def assign_many(
    db: AsyncSession,
    cliente_id: int,
    payload: AssignManyRequest,
    assigned_by: AuthUser | None = None,
) -> ClienteRead:
    c = await _load_cliente(db, cliente_id)
    target = {sv.id: sv for sv in c.servicios if sv.id in payload.servicio_ids}
    missing = set(payload.servicio_ids) - target.keys()
    if missing:
        raise NotFound(f"servicios no encontrados en el turno: {sorted(missing)}")

    st = await staff_service.get_or_404(db, payload.staff_numero)
    effective = await staff_service.get_read_or_404(db, payload.staff_numero)
    if effective.status != EffectiveStatus.DISPONIBLE:
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
    actor = _actor_fields(assigned_by)
    for sv in target.values():
        sv.staff_numero = payload.staff_numero
        sv.estado = ServicioEstado.EN_ATENCION
        sv.asignado_por_role = actor["role"]
        sv.asignado_por_subject = actor["subject"]
        sv.asignado_por_nombre = actor["nombre"]
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
    if all(
        item.estado in {ServicioEstado.FINALIZADO, ServicioEstado.CANCELADO}
        for item in c.servicios
    ):
        c.activo = False
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def rest_service(
    db: AsyncSession, cliente_id: int, servicio_id: int
) -> ClienteRead:
    _, service = await _get_servicio(db, cliente_id, servicio_id)
    if service.estado != ServicioEstado.EN_ATENCION:
        raise BadRequest("solo un servicio EN_ATENCION puede pasar a reposo")
    service.estado = ServicioEstado.REPOSO
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def resume_service(
    db: AsyncSession, cliente_id: int, servicio_id: int
) -> ClienteRead:
    _, service = await _get_servicio(db, cliente_id, servicio_id)
    if service.estado != ServicioEstado.REPOSO:
        raise BadRequest("solo un servicio EN_REPOSO puede reanudarse")
    if service.staff_numero is None:
        raise BadRequest("el servicio no tiene especialista asignado")
    staff = await staff_service.get_or_404(db, service.staff_numero)
    if staff.manual_status != ManualStatus.DISPONIBLE:
        raise BadRequest(
            f"el especialista {staff.alias} no está disponible para reanudar"
        )
    service.estado = ServicioEstado.EN_ATENCION
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def change_specialist(
    db: AsyncSession,
    cliente_id: int,
    servicio_id: int,
    payload: ChangeSpecialistRequest,
    changed_by: AuthUser | None = None,
) -> ClienteRead:
    c, sv = await _get_servicio(db, cliente_id, servicio_id)
    if sv.estado in {ServicioEstado.FINALIZADO, ServicioEstado.CANCELADO}:
        raise BadRequest("no se puede cambiar el especialista de un servicio finalizado")
    await _validate_staff_for_area(db, payload.staff_numero, sv.area_key)

    actor = _actor_fields(changed_by)
    sv.cambios.append(
        ServicioCambio(
            de_staff=sv.staff_numero,
            a_staff=payload.staff_numero,
            motivo="Cambio administrativo",
            cambiado_por_role=actor["role"],
            cambiado_por_subject=actor["subject"],
            cambiado_por_nombre=actor["nombre"],
        )
    )
    sv.staff_numero = payload.staff_numero
    sv.estado = ServicioEstado.EN_ATENCION
    sv.asignado_por_role = actor["role"]
    sv.asignado_por_subject = actor["subject"]
    sv.asignado_por_nombre = actor["nombre"]
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def replace_service(
    db: AsyncSession,
    cliente_id: int,
    servicio_id: int,
    payload: ServiceReplaceRequest,
    updated_by: AuthUser | None = None,
) -> ClienteRead:
    cliente, service = await _get_servicio(db, cliente_id, servicio_id)
    if service.estado in {ServicioEstado.FINALIZADO, ServicioEstado.CANCELADO}:
        raise BadRequest("no se puede editar un servicio finalizado o eliminado")
    replacement = (await services_service.get_many_or_404(db, [payload.catalog_service_id]))[0]
    if service.staff_numero is not None and service.area_key != replacement.area_key:
        service.staff_numero = None
        service.estado = ServicioEstado.PENDIENTE
    service.area_key = replacement.area_key
    service.nombre = replacement.nombre
    service.precio_usd = replacement.precio_usd
    actor = _actor_fields(updated_by)
    service.modificado_por_role = actor["role"]
    service.modificado_por_subject = actor["subject"]
    service.modificado_por_nombre = actor["nombre"]
    service.modificado_at = func.now()
    _sync_solo_unas(cliente)
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def cancel_service(
    db: AsyncSession,
    cliente_id: int,
    servicio_id: int,
    updated_by: AuthUser | None = None,
) -> ClienteRead:
    cliente, service = await _get_servicio(db, cliente_id, servicio_id)
    if service.estado in {ServicioEstado.FINALIZADO, ServicioEstado.CANCELADO}:
        raise BadRequest("no se puede eliminar un servicio finalizado o eliminado")
    if service.estado == ServicioEstado.PENDIENTE and service.staff_numero is None:
        # Un servicio que nunca se asignó es un error de captura, no una anulación
        # operativa: se elimina por completo y no deja cambio ni historial.
        cliente.servicios.remove(service)
        _sync_solo_unas(cliente)
        if not cliente.servicios:
            cliente.activo = False
        await db.commit()
        return _to_read(await _load_cliente(db, cliente_id))
    service.estado = ServicioEstado.CANCELADO
    actor = _actor_fields(updated_by)
    service.modificado_por_role = actor["role"]
    service.modificado_por_subject = actor["subject"]
    service.modificado_por_nombre = actor["nombre"]
    service.modificado_at = func.now()
    _sync_solo_unas(cliente)
    if all(
        item.estado in {ServicioEstado.FINALIZADO, ServicioEstado.CANCELADO}
        for item in cliente.servicios
    ):
        cliente.activo = False
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))


async def update_staff_preferences(
    db: AsyncSession,
    cliente_id: int,
    payload: StaffPreferencesUpdate,
    updated_by: AuthUser | None = None,
) -> ClienteRead:
    cliente = await _load_cliente(db, cliente_id)
    await _apply_staff_preferences(
        db, cliente, payload.staff_numeros, payload.acepta_otro_estilista
    )
    actor = _actor_fields(updated_by)
    cliente.actualizado_por_role = actor["role"]
    cliente.actualizado_por_subject = actor["subject"]
    cliente.actualizado_por_nombre = actor["nombre"]
    await db.commit()
    return _to_read(await _load_cliente(db, cliente_id))
