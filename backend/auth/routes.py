import uuid
import logging

from fastapi import APIRouter, HTTPException, Response, Depends
from jose import JWTError

from backend.auth.core import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from backend.auth.schemas import (
    UserRegister, UserLogin, UserOut, TokenResponse,
    RefreshRequest, PasswordChange,
)
from backend.auth.dependencies import get_current_user
from backend.db.connection import get_app_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_OPTS = dict(httponly=True, samesite="lax", max_age=86400 * 30)


def _build_token_response(user_id: str, email: str, full_name: str | None, response: Response) -> TokenResponse:
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    response.set_cookie("qm_token", access, **_COOKIE_OPTS)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserOut(id=user_id, email=email, full_name=full_name, is_active=True),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: UserRegister, response: Response):
    async with get_app_connection() as conn:
        if await conn.fetchval("SELECT 1 FROM users WHERE email = $1", data.email):
            raise HTTPException(status_code=409, detail="Email already registered")

        user_id = str(uuid.uuid4())
        await conn.execute(
            "INSERT INTO users (id, email, hashed_password, full_name) VALUES ($1::uuid, $2, $3, $4)",
            user_id, data.email, hash_password(data.password), data.full_name,
        )
        # Give new user a demo connection so they see data immediately
        await conn.execute(
            """INSERT INTO user_db_connections (user_id, name, db_type, connection_string, is_demo)
               VALUES ($1::uuid, 'Demo Database', 'postgresql', 'demo', true)""",
            user_id,
        )

    logger.info(f"New user registered: {data.email}")
    return _build_token_response(user_id, data.email, data.full_name, response)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, response: Response):
    async with get_app_connection() as conn:
        row = await conn.fetchrow(
            "SELECT id::text, email, hashed_password, full_name, is_active FROM users WHERE email = $1",
            data.email,
        )

    if not row or not verify_password(data.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Account is disabled")

    logger.info(f"User logged in: {data.email}")
    return _build_token_response(row["id"], row["email"], row["full_name"], response)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, response: Response):
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub", "")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    async with get_app_connection() as conn:
        row = await conn.fetchrow(
            "SELECT id::text, email, full_name, is_active FROM users WHERE id = $1::uuid",
            user_id,
        )

    if not row or not row["is_active"]:
        raise HTTPException(status_code=401, detail="User not found")

    return _build_token_response(row["id"], row["email"], row["full_name"], response)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("qm_token")
    return {"status": "logged out"}


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return UserOut(**user)


@router.put("/password")
async def change_password(data: PasswordChange, user: dict = Depends(get_current_user)):
    async with get_app_connection() as conn:
        row = await conn.fetchrow(
            "SELECT hashed_password FROM users WHERE id = $1::uuid", user["id"]
        )
        if not verify_password(data.current_password, row["hashed_password"]):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        await conn.execute(
            "UPDATE users SET hashed_password = $1 WHERE id = $2::uuid",
            hash_password(data.new_password), user["id"],
        )
    return {"status": "password updated"}
