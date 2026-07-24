from typing import Annotated

from fastapi import Depends

from src.dependencies import DbSession
from src.items import service
from src.items.exceptions import ItemNotFound
from src.items.models import Item


async def valid_item_id(item_id: int, db: DbSession) -> Item:
    """Validate existence in one place so routes can assume the item is present."""
    item = await service.get_item(db, item_id)
    if not item:
        raise ItemNotFound()
    return item


ValidItem = Annotated[Item, Depends(valid_item_id)]
