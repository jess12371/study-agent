# Skema Pydantic untuk autentikasi (F-09).

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    # Payload signup.
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=200)


class UserLogin(BaseModel):
    # Payload login.
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    # Data user yang aman ditampilkan (tanpa password).
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str | None = None
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    # Respons setelah signup/login.
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
