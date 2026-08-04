from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.turnos.constants import EtiquetaCodigo, ServicioEstado, SituacionTurno, TurnoEstado


class CheckInRequest(BaseModel):
    """Payload del check-in del cliente."""

    cedula: str = Field(
        min_length=6,
        max_length=20,
        pattern=r"^(?:[VEve]-?)?[\d\.]{6,20}$",
        description="Cédula. Formato flexible; se acepta 'V-10.805.030' o 'V12345678'.",
    )
    nombre: str = Field(min_length=2, max_length=128)
    telefono: str = Field(min_length=7, max_length=25)
    direccion: str = Field(min_length=2, max_length=255)
    observacion: str = Field(default="", max_length=1000)
    etiquetas: list[EtiquetaCodigo] = Field(default_factory=list, max_length=9)
    service_ids: list[int] = Field(min_length=1)
    active_turno_id: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Turno activo seleccionado durante la búsqueda. Si coincide con la cédula, "
            "los servicios se agregan a esa visita."
        ),
    )


class CambioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ts: datetime
    de_staff: int | None
    a_staff: int
    motivo: str
    cambiado_por_nombre: str | None = None


class TurnoServicioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    area_key: str
    nombre: str
    precio_usd: Decimal
    staff_numero: int | None
    estado: ServicioEstado
    pendientes_area: int = 0
    asignado_por_nombre: str | None = None
    cambios: list[CambioRead] = Field(default_factory=list)


class ClienteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    turno: int
    cedula: str
    nombre: str
    telefono: str
    direccion: str
    observacion: str
    etiquetas: list[EtiquetaCodigo]
    situacion: SituacionTurno
    activo: bool
    registrado_por_role: str | None
    registrado_por_subject: str | None
    registrado_por_nombre: str | None
    actualizado_por_nombre: str | None
    created_at: datetime
    estado: TurnoEstado
    servicios: list[TurnoServicioRead]


class AssignRequest(BaseModel):
    staff_numero: int = Field(gt=0)


class AssignManyRequest(BaseModel):
    servicio_ids: list[int] = Field(min_length=1)
    staff_numero: int = Field(gt=0)


class ChangeSpecialistRequest(BaseModel):
    """Cambio de especialista a mitad de turno. Requiere PIN + motivo."""

    staff_numero: int = Field(gt=0)
    pin: str = Field(min_length=1)
    motivo: str = Field(min_length=1, max_length=500)


class SituacionUpdate(BaseModel):
    situacion: SituacionTurno


class ClienteProfileRead(BaseModel):
    id: int
    cedula: str
    nombre: str
    telefono: str
    direccion: str
    active_turno_id: int | None = None
    active_turno: int | None = None
    alerta_estafa: bool = False


class ClienteProfileSummary(ClienteProfileRead):
    visitas: int
    ultima_visita: datetime | None
    etiquetas: list[EtiquetaCodigo] = Field(default_factory=list)


class ClienteHistoryServiceRead(BaseModel):
    id: int
    area_key: str
    nombre: str
    precio_usd: Decimal
    staff_numero: int | None
    especialista: str | None
    estado: ServicioEstado


class ClienteHistoryVisitRead(BaseModel):
    id: int
    turno: int
    created_at: datetime
    observacion: str
    etiquetas: list[EtiquetaCodigo] = Field(default_factory=list)
    situacion: SituacionTurno
    activo: bool
    registrado_por_nombre: str | None
    estado: TurnoEstado
    servicios: list[ClienteHistoryServiceRead] = Field(default_factory=list)


class ClienteProfileDetail(ClienteProfileRead):
    visitas: list[ClienteHistoryVisitRead] = Field(default_factory=list)


class TurnoDetailsUpdate(BaseModel):
    observacion: str = Field(default="", max_length=1000)
    etiquetas: list[EtiquetaCodigo] = Field(default_factory=list, max_length=9)


class PublicQueueRead(BaseModel):
    atendiendo: list[int]
    en_reposo: list[int]
    en_espera: list[int]
    ultimo_cambio: datetime | None


class QueuePositionRead(BaseModel):
    id: int
    turno: int
    nombre: str
    estado: TurnoEstado
    prioridad_int: bool
    posicion: int | None
    personas_delante: int
