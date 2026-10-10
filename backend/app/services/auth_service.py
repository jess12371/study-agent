# Service autentikasi (F-09) — registrasi & login.

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.auth import TokenResponse, UserRegister, UserResponse

logger = logging.getLogger(__name__)


def register_user(db: Session, data: UserRegister) -> User:
    # Buat user baru. Email dinormalisasi lowercase dan harus unik.
    email = str(data.email).strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        logger.info("Signup ditolak: email sudah terdaftar")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered.",
        )

    user = User(
        email=email,
        name=data.name,
        password_hash=hash_password(data.password),  # password tidak pernah di-log
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User baru terdaftar: id=%s", user.id)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    # Verifikasi kredensial. Return None kalau email/password salah.
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def build_token_response(user: User) -> TokenResponse:
    # Susun access token + data user untuk respons signup/login.
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )
