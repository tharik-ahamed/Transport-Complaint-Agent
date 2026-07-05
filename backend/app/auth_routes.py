"""
Auth Routes — Warning 2 Fix
=============================
POST /api/v1/auth/login  — public endpoint; returns a JWT on valid credentials
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.auth import create_access_token, verify_admin_credentials

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


@router.post("/login", response_model=TokenResponse, summary="Admin login — returns JWT")
async def login(credentials: LoginRequest):
    """
    Authenticate with admin username and password.
    Returns a Bearer JWT token valid for 8 hours.

    Default credentials (change via .env):
      username: admin
      password: admin123
    """
    if not verify_admin_credentials(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
    token = create_access_token(data={"sub": credentials.username, "role": "admin"})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
