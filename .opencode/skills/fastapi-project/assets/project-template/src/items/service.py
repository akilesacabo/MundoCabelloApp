from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.items.models import Item
from src.items.schemas import ItemCreate


async def create_item(db: AsyncSession, data: ItemCreate) -> Item:
    item = Item(name=data.name, description=data.description)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def get_item(db: AsyncSession, item_id: int) -> Item | None:
    return await db.get(Item, item_id)


async def list_items(
    db: AsyncSession, limit: int, offset: int
) -> tuple[list[Item], int]:
    total = await db.scalar(select(func.count()).select_from(Item)) or 0
    result = await db.execute(
        select(Item).order_by(Item.id).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total
