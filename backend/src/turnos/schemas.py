from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.turnos.constants import ServicioEstado, SituacionTurno, TurnoEstado


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
    service_ids: list[int] = Field(min_length=1)


class CambioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ts: datetime
    de_staff: int | None
    a_staff: int
    motivo: str


class TurnoServicioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    area_key: str
    nombre: str
    precio_usd: Decimal
    staff_numero: int | None
    estado: ServicioEstado
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
    situacion: SituacionTurno
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
    cedula: str
    nombre: str
    telefono: str
    direccion: str


class PublicQueueRead(BaseModel):
    atendiendo: list[int]
    en_espera: list[int]
    ultimo_cambio: datetime | None
