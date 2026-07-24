from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base


class Area(Base):
    __tablename__ = "area"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    color: Mapped[str] = mapped_column(String(16))

    services: Mapped[list[ServiceCatalog]] = relationship(back_populates="area")


class ServiceCatalog(Base):
    """Catálogo de servicios ofrecidos. Snapshot de precio se copia al turno."""

    __tablename__ = "service_catalog"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(128), index=True)
    area_key: Mapped[str] = mapped_column(
        ForeignKey("area.key", ondelete="RESTRICT"), index=True
    )
    precio_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    area: Mapped[Area] = relationship(back_populates="services")
