# Service autentikasi (F-09) — registrasi, login, dan verifikasi OTP (mock).

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import TokenResponse, UserRegister, UserResponse

logger = logging.getLogger(__name__)

OTP_TTL_MINUTES = 10


def _generate_otp() -> str:
    # 6 digit acak yang aman.
    return f"{secrets.randbelow(1_000_000):06d}"


def _issue_otp(user: User) -> str:
    # Set OTP baru + masa berlaku; log/print untuk mode mock.
    otp = _generate_otp()
    user.otp_code = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)
    user.is_verified = False
    logger.warning("OTP untuk %s: %s", user.email, otp)
    print(f"[MOCK OTP] {user.email}: {otp}", flush=True)
    return otp


def register_user(db: Session, data: UserRegister) -> User:
    # Buat user baru (belum terverifikasi) + kirim OTP mock.
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
        is_verified=False,
    )
    _issue_otp(user)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User baru terdaftar (menunggu OTP): id=%s", user.id)
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


def verify_otp(db: Session, email: str, otp: str) -> User:
    # Validasi OTP; tandai user terverifikasi.
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not user.otp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP."
        )
    expires_at = user.otp_expires_at
    if expires_at is not None and expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OTP has expired."
        )
    if not secrets.compare_digest(user.otp_code, otp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect OTP."
        )

    user.is_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    db.commit()
    db.refresh(user)
    logger.info("Email terverifikasi: id=%s", user.id)
    return user


def resend_otp(db: Session, email: str) -> str:
    # Kirim ulang OTP (mock).
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    otp = _issue_otp(user)
    db.commit()
    return otp


def build_token_response(user: User) -> TokenResponse:
    # Susun access token + data user untuk respons signup/login/verify.
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )
