from typing import Annotated

from fastapi import APIRouter, Query

from src.auth.dependencies import AdminUser
from src.dependencies import DbSession
from src.historial import service as historial_service
from src.historial.schemas import HistorialRead, HistorialSummaryRead

router = APIRouter(prefix="/historial", tags=["historial"])


@router.get("", response_model=list[HistorialRead])
async def list_historial(
    db: DbSession,
    admin: AdminUser,
    cliente: Annotated[str | None, Query(description="Match parcial en nombre o cédula")] = None,
    staff: Annotated[int | None, Query(description="Número del especialista")] = None,
    servicio: Annotated[
        str | None, Query(description="Match parcial en nombre del servicio")
    ] = None,
    area: Annotated[str | None, Query(description="area_key exacta")] = None,
    limit: int = 200,
) -> list[HistorialRead]:
    rows = await historial_service.list_historial(
        db,
        cliente=cliente,
        staff_numero=staff,
        servicio=servicio,
        area=area,
        limit=limit,
    )
    return [HistorialRead.model_validate(r) for r in rows]


@router.get("/summary", response_model=HistorialSummaryRead)
async def historial_summary(
    db: DbSession,
    admin: AdminUser,
    cliente: Annotated[str | None, Query(description="Match parcial en nombre o cédula")] = None,
    staff: Annotated[int | None, Query(description="Número del especialista")] = None,
    servicio: Annotated[
        str | None, Query(description="Match parcial en nombre del servicio")
    ] = None,
    area: Annotated[str | None, Query(description="area_key exacta")] = None,
) -> HistorialSummaryRead:
    return await historial_service.get_summary(
        db,
        cliente=cliente,
        staff_numero=staff,
        servicio=servicio,
        area=area,
    )
