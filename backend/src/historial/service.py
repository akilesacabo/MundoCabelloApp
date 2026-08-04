from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.historial.models import Historial
from src.historial.schemas import HistorialAreaSummary, HistorialSummaryRead


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


def _filtered_stmt(
    cliente: str | None = None,
    staff_numero: int | None = None,
    servicio: str | None = None,
    area: str | None = None,
):
    stmt = select(Historial)
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
    return stmt


async def get_summary(
    db: AsyncSession,
    cliente: str | None = None,
    staff_numero: int | None = None,
    servicio: str | None = None,
    area: str | None = None,
) -> HistorialSummaryRead:
    base = _filtered_stmt(cliente, staff_numero, servicio, area).subquery()
    totals = await db.execute(
        select(
            func.count(base.c.id),
            func.coalesce(func.sum(base.c.precio_usd), 0),
        )
    )
    total_count, total_usd = totals.one()
    area_rows = await db.execute(
        select(
            base.c.area_key,
            func.count(base.c.id),
            func.coalesce(func.sum(base.c.precio_usd), 0),
        )
        .group_by(base.c.area_key)
        .order_by(base.c.area_key)
    )
    return HistorialSummaryRead(
        total_servicios=int(total_count or 0),
        total_usd=Decimal(str(total_usd or 0)),
        por_area=[
            HistorialAreaSummary(
                area_key=row[0],
                total_servicios=int(row[1] or 0),
                total_usd=Decimal(str(row[2] or 0)),
            )
            for row in area_rows.all()
        ],
    )
