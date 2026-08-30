from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class HistorialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ts: datetime
    cliente_id: int
    cliente_nombre: str
    cliente_cedula: str
    servicio_nombre: str
    area_key: str
    precio_base_usd: Decimal
    ajuste_usd: Decimal
    precio_total_usd: Decimal
    precio_usd: Decimal
    staff_numero: int | None
    staff_nombre: str


class HistorialAreaSummary(BaseModel):
    area_key: str
    total_servicios: int
    total_usd: Decimal


class HistorialSummaryRead(BaseModel):
    total_servicios: int
    total_usd: Decimal
    por_area: list[HistorialAreaSummary]
