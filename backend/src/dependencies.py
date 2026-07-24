from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db

# Reusable typed alias for the modern Annotated dependency style.
DbSession = Annotated[AsyncSession, Depends(get_db)]
