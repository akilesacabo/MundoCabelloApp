from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, func
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


class Promocion(Base):
    """Oferta comercial compuesta por servicios que se asignan por separado."""

    __tablename__ = "promocion"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    precio_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    servicios: Mapped[list[PromocionServicio]] = relationship(
        back_populates="promocion",
        cascade="all, delete-orphan",
        order_by="PromocionServicio.id",
    )


class PromocionServicio(Base):
    """Servicio incluido y su precio especial dentro de una promoción."""

    __tablename__ = "promocion_servicio"

    id: Mapped[int] = mapped_column(primary_key=True)
    promocion_id: Mapped[int] = mapped_column(
        ForeignKey("promocion.id", ondelete="CASCADE"), index=True
    )
    service_catalog_id: Mapped[int] = mapped_column(
        ForeignKey("service_catalog.id", ondelete="RESTRICT"), index=True
    )
    precio_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    promocion: Mapped[Promocion] = relationship(back_populates="servicios")
    servicio: Mapped[ServiceCatalog] = relationship()
