"""JWT-based authentication for the dummy single admin account."""

from datetime import datetime, timedelta, timezone
from secrets import compare_digest

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.core.settings import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def authenticate_user(username: str, password: str) -> bool:
    """Check credentials against the single dummy admin account."""
    settings = get_settings()
    return compare_digest(username, settings.admin_username) and compare_digest(
        password, settings.admin_password
    )


def create_access_token(subject: str) -> str:
    """Issue a signed JWT for the given subject (username)."""
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Decode the bearer token and return the authenticated username, or raise 401."""
    settings = get_settings()
    invalid_token_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise invalid_token_error from exc

    username = payload.get("sub")
    if username is None:
        raise invalid_token_error
    return username
