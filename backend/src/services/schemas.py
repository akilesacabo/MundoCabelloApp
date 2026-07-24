from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AreaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    name: str
    color: str


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    area_key: str
    precio_usd: Decimal


class ServicesGrouped(BaseModel):
    """Catálogo agrupado por área para el picker del check-in."""

    area: AreaRead
    servicios: list[ServiceRead]


class ServiceCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=128)
    area_key: str = Field(min_length=2, max_length=32)
    precio_usd: Decimal = Field(ge=0)


class ServiceUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=128)
    area_key: str | None = Field(default=None, min_length=2, max_length=32)
    precio_usd: Decimal | None = Field(default=None, ge=0)
