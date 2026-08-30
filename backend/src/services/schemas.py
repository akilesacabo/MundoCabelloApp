from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AreaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    name: str
    color: str
    activo: bool


class AreaCreate(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class AreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=64)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    area_key: str
    precio_usd: Decimal
    activo: bool


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


class PromotionCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=128)
    servicios: list["PromotionServiceInput"] = Field(min_length=1)


class PromotionUpdate(PromotionCreate):
    pass


class PromotionServiceInput(BaseModel):
    service_id: int = Field(gt=0)
    precio_usd: Decimal = Field(ge=0)


class PromotionServiceRead(BaseModel):
    service_id: int
    nombre: str
    area_key: str
    precio_usd: Decimal


class PromotionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    precio_usd: Decimal
    activo: bool
    servicios: list[PromotionServiceRead]
