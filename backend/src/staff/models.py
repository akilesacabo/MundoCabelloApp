from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base
from src.services.models import Area
from src.staff.constants import ManualStatus

staff_area = Table(
    "staff_area",
    Base.metadata,
    Column("staff_numero", ForeignKey("staff.numero", ondelete="CASCADE"), primary_key=True),
    Column("area_key", ForeignKey("area.key", ondelete="RESTRICT"), primary_key=True),
)


class Staff(Base):
    """Especialista. `numero` es la identidad estable dentro del negocio."""

    __tablename__ = "staff"

    numero: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    alias: Mapped[str] = mapped_column(String(64))
    nombre: Mapped[str] = mapped_column(String(128))
    cedula: Mapped[str] = mapped_column(String(20))
    initials: Mapped[str] = mapped_column(String(4))
    manual_status: Mapped[str] = mapped_column(
        String(16), default=ManualStatus.DISPONIBLE, index=True
    )
    en_prueba: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    areas: Mapped[list[Area]] = relationship(secondary=staff_area, lazy="selectin")
