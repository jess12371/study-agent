# Utilitas keamanan — hashing password (bcrypt) dan JWT (HS256).

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    # Hash password dengan bcrypt + salt acak. Hasil dikembalikan sebagai string.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Bandingkan password plaintext dengan hash. False kalau hash tidak valid.
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    user_id: uuid.UUID, expires_minutes: int | None = None
) -> str:
    # Buat JWT HS256 dengan payload sub/iat/exp.
    minutes = expires_minutes or settings.access_token_expire_minutes
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    # Decode + verifikasi token. Raise jwt.PyJWTError kalau invalid/expired.
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
