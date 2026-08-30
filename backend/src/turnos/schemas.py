from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.turnos.constants import EtiquetaCodigo, ServicioEstado, SituacionTurno, TurnoEstado

AdjustmentAmount = Literal[0, 5, 10, 15, 20, 25, 30]


class ServiceAdjustmentInput(BaseModel):
    service_id: int = Field(gt=0)
    ajuste_usd: AdjustmentAmount


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
    service_ids: list[int] = Field(default_factory=list)
    promotion_ids: list[int] = Field(default_factory=list)
    ajustes: list[ServiceAdjustmentInput] = Field(default_factory=list)
    staff_numeros_preseleccion: list[int] = Field(default_factory=list, max_length=3)
    acepta_otro_estilista: bool = False
    active_turno_id: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Turno activo seleccionado durante la búsqueda. Si coincide con la cédula, "
            "los servicios se agregan a esa visita."
        ),
    )

    @model_validator(mode="after")
    def requires_a_service_or_promotion(self) -> "CheckInRequest":
        if not self.service_ids and not self.promotion_ids:
            raise ValueError("debe indicar al menos un servicio o promoción")
        return self


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
    ajuste_usd: Decimal
    precio_total_usd: Decimal
    origen: str
    promocion_id: int | None
    ajuste_por_nombre: str | None = None
    ajuste_at: datetime | None = None
    staff_numero: int | None
    estado: ServicioEstado
    pendientes_area: int = 0
    asignado_por_nombre: str | None = None
    modificado_por_nombre: str | None = None
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
    preseleccion_staff_numeros: list[int] = Field(default_factory=list)
    acepta_otro_estilista: bool = False
    created_at: datetime
    estado: TurnoEstado
    servicios: list[TurnoServicioRead]


class AssignRequest(BaseModel):
    staff_numero: int = Field(gt=0)
    confirmar_ocupado: bool = False


class AssignManyRequest(BaseModel):
    servicio_ids: list[int] = Field(min_length=1)
    staff_numero: int = Field(gt=0)


class ChangeSpecialistRequest(BaseModel):
    """Cambio de especialista autorizado por el rol administrador."""

    staff_numero: int = Field(gt=0)


class ServiceReplaceRequest(BaseModel):
    catalog_service_id: int = Field(gt=0)


class ServiceAdjustmentUpdate(BaseModel):
    ajuste_usd: AdjustmentAmount


class StaffPreferencesUpdate(BaseModel):
    staff_numeros: list[int] = Field(default_factory=list, max_length=3)
    acepta_otro_estilista: bool = False


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
    ajuste_usd: Decimal
    precio_total_usd: Decimal
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
    atendiendo: list["PublicQueueClientRead"]
    en_reposo: list["PublicQueueClientRead"]
    en_espera: list["PublicQueueClientRead"]
    ultimo_cambio: datetime | None
    por_area: list["AreaQueueRead"] = Field(default_factory=list)


class PublicQueueClientRead(BaseModel):
    turno: int
    nombre: str


class AreaQueueItemRead(BaseModel):
    cliente_id: int
    servicio_id: int
    turno: int
    cliente_nombre: str
    servicio_nombre: str
    estado: ServicioEstado
    posicion: int | None = None
    personas_delante: int = 0


class AreaQueueRead(BaseModel):
    area_key: str
    atendiendo: list[AreaQueueItemRead] = Field(default_factory=list)
    en_reposo: list[AreaQueueItemRead] = Field(default_factory=list)
    en_espera: list[AreaQueueItemRead] = Field(default_factory=list)


class QueuePositionRead(BaseModel):
    id: int
    turno: int
    nombre: str
    estado: TurnoEstado
    prioridad_int: bool
    posicion: int | None
    personas_delante: int
    areas: list["QueuePositionAreaRead"] = Field(default_factory=list)


class QueuePositionAreaRead(BaseModel):
    area_key: str
    servicio_id: int
    servicio_nombre: str
    estado: ServicioEstado
    posicion: int | None
    personas_delante: int
