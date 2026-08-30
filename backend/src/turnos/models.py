from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base
from src.staff.models import Staff
from src.turnos.constants import ServicioEstado, SituacionTurno


class ClienteProfile(Base):
    """Ficha permanente del cliente, única por cédula normalizada."""

    __tablename__ = "cliente_perfil"

    id: Mapped[int] = mapped_column(primary_key=True)
    cedula: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(128), index=True)
    telefono: Mapped[str] = mapped_column(String(25))
    direccion: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    turnos: Mapped[list[Cliente]] = relationship(back_populates="perfil")


class Cliente(Base):
    """Un check-in del cliente = un turno. El "estado" del turno es derivado."""

    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(primary_key=True)
    turno: Mapped[int] = mapped_column(index=True)
    perfil_id: Mapped[int | None] = mapped_column(
        ForeignKey("cliente_perfil.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cedula: Mapped[str] = mapped_column(String(20), index=True)
    nombre: Mapped[str] = mapped_column(String(128))
    telefono: Mapped[str] = mapped_column(String(20))
    direccion: Mapped[str] = mapped_column(String(255))
    observacion: Mapped[str] = mapped_column(Text, default="")
    situacion: Mapped[str] = mapped_column(String(16), default=SituacionTurno.PRESENTE, index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    registrado_por_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    registrado_por_subject: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registrado_por_nombre: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actualizado_por_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    actualizado_por_subject: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actualizado_por_nombre: Mapped[str | None] = mapped_column(String(128), nullable=True)
    acepta_otro_estilista: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    perfil: Mapped[ClienteProfile | None] = relationship(back_populates="turnos")
    servicios: Mapped[list[TurnoServicio]] = relationship(
        back_populates="cliente",
        cascade="all, delete-orphan",
        order_by="TurnoServicio.id",
    )
    etiquetas: Mapped[list[ClienteEtiqueta]] = relationship(
        back_populates="cliente",
        cascade="all, delete-orphan",
        order_by="ClienteEtiqueta.codigo",
    )
    preselecciones: Mapped[list[ClientePreseleccion]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan", order_by="ClientePreseleccion.id"
    )


class ClienteEtiqueta(Base):
    """Etiqueta operativa aplicada a una visita/check-in."""

    __tablename__ = "cliente_etiqueta"
    __table_args__ = (UniqueConstraint("cliente_id", "codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("cliente.id", ondelete="CASCADE"), index=True
    )
    codigo: Mapped[str] = mapped_column(String(16), index=True)

    cliente: Mapped[Cliente] = relationship(back_populates="etiquetas")


class ClientePreseleccion(Base):
    """Preferencias de especialista de una visita; máximo tres se valida en API."""

    __tablename__ = "cliente_preseleccion"
    __table_args__ = (UniqueConstraint("cliente_id", "staff_numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("cliente.id", ondelete="CASCADE"), index=True
    )
    staff_numero: Mapped[int] = mapped_column(
        ForeignKey("staff.numero", ondelete="RESTRICT"), index=True
    )

    cliente: Mapped[Cliente] = relationship(back_populates="preselecciones")
    staff: Mapped[Staff] = relationship()


class TurnoServicio(Base):
    """Un servicio dentro de un turno. Cada uno se asigna individualmente."""

    __tablename__ = "turno_servicio"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("cliente.id", ondelete="CASCADE"), index=True
    )
    area_key: Mapped[str] = mapped_column(ForeignKey("area.key", ondelete="RESTRICT"), index=True)
    nombre: Mapped[str] = mapped_column(String(128))
    precio_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    origen: Mapped[str] = mapped_column(String(16), default="legacy", index=True)
    promocion_id: Mapped[int | None] = mapped_column(
        ForeignKey("promocion.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    ajuste_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    ajuste_por_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ajuste_por_subject: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ajuste_por_nombre: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ajuste_at: Mapped[datetime | None] = mapped_column(nullable=True)
    staff_numero: Mapped[int | None] = mapped_column(
        ForeignKey("staff.numero", ondelete="SET NULL"), nullable=True, index=True
    )
    estado: Mapped[str] = mapped_column(String(16), default=ServicioEstado.PENDIENTE, index=True)
    asignado_por_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    asignado_por_subject: Mapped[str | None] = mapped_column(String(64), nullable=True)
    asignado_por_nombre: Mapped[str | None] = mapped_column(String(128), nullable=True)
    modificado_por_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    modificado_por_subject: Mapped[str | None] = mapped_column(String(64), nullable=True)
    modificado_por_nombre: Mapped[str | None] = mapped_column(String(128), nullable=True)
    modificado_at: Mapped[datetime | None] = mapped_column(nullable=True)

    cliente: Mapped[Cliente] = relationship(back_populates="servicios")
    staff: Mapped[Staff | None] = relationship()
    cambios: Mapped[list[ServicioCambio]] = relationship(
        back_populates="servicio",
        cascade="all, delete-orphan",
        order_by="ServicioCambio.ts",
    )

    @property
    def precio_total_usd(self) -> Decimal:
        return self.precio_usd + self.ajuste_usd


class ServicioCambio(Base):
    """Log de reasignaciones de un servicio autorizadas por rol administrador."""

    __tablename__ = "servicio_cambio"

    id: Mapped[int] = mapped_column(primary_key=True)
    turno_servicio_id: Mapped[int] = mapped_column(
        ForeignKey("turno_servicio.id", ondelete="CASCADE"), index=True
    )
    ts: Mapped[datetime] = mapped_column(server_default=func.now())
    de_staff: Mapped[int | None] = mapped_column(
        ForeignKey("staff.numero", ondelete="SET NULL"), nullable=True
    )
    a_staff: Mapped[int] = mapped_column(ForeignKey("staff.numero", ondelete="RESTRICT"))
    motivo: Mapped[str] = mapped_column(Text)
    cambiado_por_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cambiado_por_subject: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cambiado_por_nombre: Mapped[str | None] = mapped_column(String(128), nullable=True)

    servicio: Mapped[TurnoServicio] = relationship(back_populates="cambios")
