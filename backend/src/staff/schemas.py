from pydantic import BaseModel, ConfigDict, Field

from src.staff.constants import EffectiveStatus, ManualStatus


class StaffActivo(BaseModel):
    """Servicio que el especialista está atendiendo ahora mismo."""

    cliente_id: int
    turno: int
    cliente: str
    servicio: str
    estado: str


class StaffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero: int
    alias: str
    nombre: str
    cedula: str
    initials: str
    areas: list[str]
    manual_status: ManualStatus
    en_prueba: bool
    activo: bool
    # Campos derivados (los llena el service layer):
    status: EffectiveStatus
    activos: list[StaffActivo] = Field(default_factory=list)
    preseleccion_count: int = 0
    preseleccion_por_area: dict[str, int] = Field(default_factory=dict)


class ManualStatusUpdate(BaseModel):
    manual_status: ManualStatus


class StaffCreate(BaseModel):
    numero: int = Field(gt=0)
    alias: str = Field(min_length=1, max_length=64)
    nombre: str = Field(min_length=2, max_length=128)
    cedula: str = Field(min_length=3, max_length=20)
    areas: list[str] = Field(min_length=1)
    en_prueba: bool = False


class StaffUpdate(BaseModel):
    alias: str | None = Field(default=None, min_length=1, max_length=64)
    nombre: str | None = Field(default=None, min_length=2, max_length=128)
    cedula: str | None = Field(default=None, min_length=3, max_length=20)
    areas: list[str] | None = Field(default=None, min_length=1)
    en_prueba: bool | None = None
