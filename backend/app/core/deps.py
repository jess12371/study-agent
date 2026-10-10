# Dependency FastAPI — ambil user yang sedang login dari Bearer token.

import logging
import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# auto_error=False agar kita bisa kembalikan 401 dengan pesan konsisten.
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    # Decode token → cari user di DB. Semua kegagalan → 401.
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Not authenticated.")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(str(payload.get("sub")))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise _unauthorized("Invalid or expired token.")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("User not found or inactive.")

    return user
