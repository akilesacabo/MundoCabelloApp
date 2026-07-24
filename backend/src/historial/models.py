from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class Historial(Base):
    """Snapshot denormalizado de un servicio finalizado. Es la tabla de consulta
    del cliente: precio y nombres quedan congelados al momento del cierre."""

    __tablename__ = "historial"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    cliente_id: Mapped[int] = mapped_column(index=True)
    cliente_nombre: Mapped[str] = mapped_column(String(128), index=True)
    cliente_cedula: Mapped[str] = mapped_column(String(20), index=True)
    servicio_nombre: Mapped[str] = mapped_column(String(128), index=True)
    area_key: Mapped[str] = mapped_column(
        ForeignKey("area.key", ondelete="RESTRICT"), index=True
    )
    precio_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    staff_numero: Mapped[int | None] = mapped_column(
        ForeignKey("staff.numero", ondelete="SET NULL"), nullable=True, index=True
    )
    staff_nombre: Mapped[str] = mapped_column(String(128))
