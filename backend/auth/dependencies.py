from typing import Optional

from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from backend.auth.core import decode_token
from backend.db.connection import get_app_connection

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    qm_token: Optional[str] = Cookie(default=None),
) -> dict:
    """
    Accepts JWT either as Authorization: Bearer <token>
    or as the httpOnly cookie 'qm_token'.
    """
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    elif qm_token:
        token = qm_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with get_app_connection() as conn:
        row = await conn.fetchrow(
            "SELECT id::text, email, full_name, is_active FROM users WHERE id = $1::uuid",
            user_id,
        )

    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return dict(row)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    qm_token: Optional[str] = Cookie(default=None),
) -> Optional[dict]:
    try:
        return await get_current_user(credentials, qm_token)
    except HTTPException:
        return None
