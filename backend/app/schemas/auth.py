# Skema Pydantic untuk autentikasi (F-09).

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    # Payload signup.
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=200)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        # Minimal 8 karakter, 1 huruf besar, 1 angka.
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must include at least 1 uppercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must include at least 1 number.")
        return value


class UserLogin(BaseModel):
    # Payload login.
    email: EmailStr
    password: str


class VerifyOtpRequest(BaseModel):
    # Verifikasi email dengan kode 6 digit (mock).
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendOtpRequest(BaseModel):
    # Minta kirim ulang kode OTP.
    email: EmailStr


class UserResponse(BaseModel):
    # Data user yang aman ditampilkan (tanpa password).
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str | None = None
    is_active: bool
    is_verified: bool = True
    created_at: datetime


class TokenResponse(BaseModel):
    # Respons setelah signup/login/verify OTP.
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
