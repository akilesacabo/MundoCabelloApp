from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.dependencies import DbSession
from src.items import service
from src.items.dependencies import ValidItem
from src.items.schemas import ItemCreate, ItemResponse
from src.pagination import Page, PageParams, pagination_params

router = APIRouter(prefix="/items", tags=["items"])

PageDep = Annotated[PageParams, Depends(pagination_params)]


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(data: ItemCreate, db: DbSession):
    # Router stays thin: no business logic, no queries — it delegates to the service.
    return await service.create_item(db, data)


@router.get("", response_model=Page[ItemResponse])
async def list_items(db: DbSession, params: PageDep):
    items, total = await service.list_items(db, params.limit, params.offset)
    return Page(items=items, total=total, limit=params.limit, offset=params.offset)


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item: ValidItem):
    return item  # guaranteed to exist by the valid_item_id dependency
