from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.schemas import AuthUser
from src.auth.service import verify_token
from src.exceptions import PermissionDenied

bearer = HTTPBearer(auto_error=False)


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise PermissionDenied("Autenticación requerida.")
    return verify_token(credentials.credentials)


CurrentUser = Annotated[AuthUser, Depends(current_user)]


async def optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthUser | None:
    if credentials is None:
        return None
    if credentials.scheme.lower() != "bearer":
        raise PermissionDenied("Autenticación inválida.")
    return verify_token(credentials.credentials)


OptionalUser = Annotated[AuthUser | None, Depends(optional_user)]


async def require_admin(user: CurrentUser) -> AuthUser:
    if user.role != "admin":
        raise PermissionDenied("Esta operación requiere rol administrador.")
    return user


AdminUser = Annotated[AuthUser, Depends(require_admin)]
