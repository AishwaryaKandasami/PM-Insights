"""Supabase JWT verification. Provides get_current_user for protected routes."""

from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import Settings, get_settings


_bearer_scheme = HTTPBearer(auto_error=False)


def _verify_supabase_jwt(token: str, settings: Settings) -> str:
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET is not configured",
        )
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return str(sub)


def _resolve_dev_user_id(settings: Settings) -> str:
    if not settings.dev_user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DEV_USER_ID is not configured for development mode",
        )
    try:
        UUID(settings.dev_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DEV_USER_ID must be a valid UUID",
        ) from exc
    return settings.dev_user_id


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> str:
    """
    Return the authenticated user's UUID as a string.

    Development: returns DEV_USER_ID without verifying JWT.
    Production: requires Bearer token verified against SUPABASE_JWT_SECRET.
    """
    if settings.is_development:
        return _resolve_dev_user_id(settings)

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _verify_supabase_jwt(credentials.credentials, settings)
