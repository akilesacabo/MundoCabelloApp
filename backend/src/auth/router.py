from fastapi import APIRouter

from src.auth import service
from src.auth.dependencies import CurrentUser
from src.auth.schemas import AuthUser, LoginRequest, TokenRead
from src.dependencies import DbSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenRead)
async def login(payload: LoginRequest, db: DbSession) -> TokenRead:
    return await service.login(db, payload)


@router.get("/me", response_model=AuthUser)
async def me(user: CurrentUser) -> AuthUser:
    return user
