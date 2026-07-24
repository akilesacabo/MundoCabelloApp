from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import AuthUser, LoginRequest, TokenRead
from src.config import settings
from src.exceptions import PermissionDenied
from src.staff import service as staff_service


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_token(user: AuthUser) -> str:
    payload = {
        "role": user.role,
        "sub": user.subject,
        "name": user.display_name,
        "exp": int(time.time()) + settings.auth_token_ttl_minutes * 60,
    }
    body = _encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(settings.auth_secret.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_encode(signature)}"


def verify_token(token: str) -> AuthUser:
    try:
        body, supplied = token.split(".", 1)
        expected = hmac.new(
            settings.auth_secret.encode(), body.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _decode(supplied)):
            raise ValueError
        payload = json.loads(_decode(body))
        if int(payload["exp"]) < int(time.time()):
            raise ValueError
        return AuthUser(
            role=payload["role"],
            subject=str(payload["sub"]),
            display_name=payload["name"],
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PermissionDenied("Token inválido o vencido.") from exc


async def login(db: AsyncSession, payload: LoginRequest) -> TokenRead:
    if payload.role == "admin":
        valid = hmac.compare_digest(payload.username, settings.admin_username)
        valid &= hmac.compare_digest(payload.password, settings.admin_password)
        if not valid:
            raise PermissionDenied("Credenciales inválidas.")
        user = AuthUser(role="admin", subject="admin", display_name="Administración")
    else:
        try:
            numero = int(payload.username)
        except ValueError as exc:
            raise PermissionDenied("Credenciales inválidas.") from exc
        staff = await staff_service.get_or_404(db, numero)
        if not hmac.compare_digest(payload.password.upper(), staff.cedula.upper()):
            raise PermissionDenied("Credenciales inválidas.")
        user = AuthUser(
            role="especialista", subject=str(staff.numero), display_name=staff.alias
        )
    return TokenRead(
        access_token=create_token(user), role=user.role, display_name=user.display_name
    )
