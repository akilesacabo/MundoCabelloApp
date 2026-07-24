from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)


class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # read straight from the ORM object

    id: int
    name: str
    description: str | None
    created_at: datetime
