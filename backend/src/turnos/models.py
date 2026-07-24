from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base
from src.staff.models import Staff
from src.turnos.constants import ServicioEstado, SituacionTurno


class Cliente(Base):
    """Un check-in del cliente = un turno. El "estado" del turno es derivado."""

    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(primary_key=True)
    turno: Mapped[int] = mapped_column(index=True)
    cedula: Mapped[str] = mapped_column(String(20), index=True)
    nombre: Mapped[str] = mapped_column(String(128))
    telefono: Mapped[str] = mapped_column(String(20))
    direccion: Mapped[str] = mapped_column(String(255))
    observacion: Mapped[str] = mapped_column(Text, default="")
    situacion: Mapped[str] = mapped_column(
        String(16), default=SituacionTurno.NORMAL, index=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    servicios: Mapped[list[TurnoServicio]] = relationship(
        back_populates="cliente",
        cascade="all, delete-orphan",
        order_by="TurnoServicio.id",
    )


class TurnoServicio(Base):
    """Un servicio dentro de un turno. Cada uno se asigna individualmente."""

    __tablename__ = "turno_servicio"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("cliente.id", ondelete="CASCADE"), index=True
    )
    area_key: Mapped[str] = mapped_column(
        ForeignKey("area.key", ondelete="RESTRICT"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(128))
    precio_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    staff_numero: Mapped[int | None] = mapped_column(
        ForeignKey("staff.numero", ondelete="SET NULL"), nullable=True, index=True
    )
    estado: Mapped[str] = mapped_column(
        String(16), default=ServicioEstado.PENDIENTE, index=True
    )

    cliente: Mapped[Cliente] = relationship(back_populates="servicios")
    staff: Mapped[Staff | None] = relationship()
    cambios: Mapped[list[ServicioCambio]] = relationship(
        back_populates="servicio",
        cascade="all, delete-orphan",
        order_by="ServicioCambio.ts",
    )


class ServicioCambio(Base):
    """Log de reasignaciones de un servicio (autorizado con PIN admin)."""

    __tablename__ = "servicio_cambio"

    id: Mapped[int] = mapped_column(primary_key=True)
    turno_servicio_id: Mapped[int] = mapped_column(
        ForeignKey("turno_servicio.id", ondelete="CASCADE"), index=True
    )
    ts: Mapped[datetime] = mapped_column(server_default=func.now())
    de_staff: Mapped[int | None] = mapped_column(
        ForeignKey("staff.numero", ondelete="SET NULL"), nullable=True
    )
    a_staff: Mapped[int] = mapped_column(
        ForeignKey("staff.numero", ondelete="RESTRICT")
    )
    motivo: Mapped[str] = mapped_column(Text)

    servicio: Mapped[TurnoServicio] = relationship(back_populates="cambios")
