# Endpoint autentikasi (F-09).

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ResendOtpRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    VerifyOtpRequest,
)
from app.services.auth_service import (
    authenticate_user,
    build_token_response,
    register_user,
    resend_otp,
    verify_otp,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    # Registrasi user baru → langsung dapat token.
    logger.info("POST /api/auth/signup")
    user = register_user(db, payload)
    return build_token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    # Login dengan email + password.
    logger.info("POST /api/auth/login")
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return build_token_response(user)


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    # Info user yang sedang login.
    return current_user


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_email_otp(
    payload: VerifyOtpRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    # Verifikasi email dengan kode 6 digit (mock OTP di log backend).
    logger.info("POST /api/auth/verify-otp")
    user = verify_otp(db, payload.email, payload.otp)
    return build_token_response(user)


@router.post("/resend-otp")
async def resend_email_otp(
    payload: ResendOtpRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    # Kirim ulang OTP (mock: tercetak di log backend).
    logger.info("POST /api/auth/resend-otp")
    resend_otp(db, payload.email)
    return {"message": "OTP sent. Check the backend logs (mock mode)."}
