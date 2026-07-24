from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.historial.models import Historial


async def list_historial(
    db: AsyncSession,
    cliente: str | None = None,
    staff_numero: int | None = None,
    servicio: str | None = None,
    area: str | None = None,
    limit: int = 200,
) -> list[Historial]:
    """Filtros case-insensitive por substring en nombres (cliente/servicio),
    exactos por staff y área. Ordena por más reciente primero.
    """
    stmt = select(Historial).order_by(Historial.ts.desc()).limit(limit)
    if cliente:
        pat = f"%{cliente.lower()}%"
        stmt = stmt.where(
            (Historial.cliente_nombre.ilike(pat))
            | (Historial.cliente_cedula.ilike(pat))
        )
    if staff_numero is not None:
        stmt = stmt.where(Historial.staff_numero == staff_numero)
    if servicio:
        stmt = stmt.where(Historial.servicio_nombre.ilike(f"%{servicio}%"))
    if area:
        stmt = stmt.where(Historial.area_key == area)
    result = await db.execute(stmt)
    return list(result.scalars().all())
