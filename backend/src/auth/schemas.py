from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["admin", "especialista"]


class LoginRequest(BaseModel):
    role: Role
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    display_name: str


class AuthUser(BaseModel):
    role: Role
    subject: str
    display_name: str
