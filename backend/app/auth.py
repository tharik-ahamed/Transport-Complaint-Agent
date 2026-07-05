"""
JWT Authentication — Warning 2 Fix
====================================
Provides:
  - create_access_token()  — mints a signed JWT
  - verify_token()         — FastAPI dependency; validates the Bearer JWT
  - verify_admin_credentials() — constant-time credential check
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
)

# HTTPBearer extractor — auto_error=False so we can return a custom 401
_bearer = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    payload = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency — validates the Bearer JWT and returns the decoded payload.
    Raises HTTP 401 if token is absent, invalid, or expired.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide a valid Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        if payload.get("sub") is None:
            raise unauthorized
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_admin_credentials(username: str, password: str) -> bool:
    """
    Constant-time comparison of admin credentials (prevents timing attacks).
    Credentials are loaded from environment variables (see config.py).
    """
    username_ok = secrets.compare_digest(username.strip(), ADMIN_USERNAME)
    password_ok = secrets.compare_digest(password.strip(), ADMIN_PASSWORD)
    return username_ok and password_ok
