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
    precio_usd: Decimal
    staff_numero: int | None
    staff_nombre: str
