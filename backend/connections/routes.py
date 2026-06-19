import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.auth.dependencies import get_current_user
from backend.db.connection import get_app_connection
from backend.tools.connection_tool import (
    test_connection, encrypt_conn_str, decrypt_conn_str
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/connections", tags=["connections"])


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    db_type: str = Field(default="postgresql", pattern=r"^(postgresql|mysql|sqlite)$")
    connection_string: str = Field(min_length=10)


class ConnectionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class ConnectionOut(BaseModel):
    id: str
    name: str
    db_type: str
    is_demo: bool
    is_active: bool
    created_at: str


@router.get("", response_model=List[ConnectionOut])
async def list_connections(user: dict = Depends(get_current_user)):
    async with get_app_connection() as conn:
        rows = await conn.fetch(
            """SELECT id::text, name, db_type, is_demo, is_active, created_at::text
               FROM user_db_connections
               WHERE user_id = $1::uuid
               ORDER BY is_demo DESC, created_at ASC""",
            user["id"],
        )
    return [dict(r) for r in rows]


@router.post("", response_model=ConnectionOut, status_code=201)
async def create_connection(data: ConnectionCreate, user: dict = Depends(get_current_user)):
    # Test the connection before saving
    ok, err = await test_connection(data.connection_string)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Cannot connect to database: {err}")

    conn_id = str(uuid.uuid4())
    encrypted = encrypt_conn_str(data.connection_string)

    async with get_app_connection() as conn:
        # Limit to 10 connections per user
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM user_db_connections WHERE user_id = $1::uuid", user["id"]
        )
        if count >= 10:
            raise HTTPException(status_code=429, detail="Maximum of 10 connections per account")

        row = await conn.fetchrow(
            """INSERT INTO user_db_connections (id, user_id, name, db_type, connection_string)
               VALUES ($1::uuid, $2::uuid, $3, $4, $5)
               RETURNING id::text, name, db_type, is_demo, is_active, created_at::text""",
            conn_id, user["id"], data.name, data.db_type, encrypted,
        )

    logger.info(f"User {user['email']} added connection '{data.name}'")
    return dict(row)


@router.patch("/{conn_id}", response_model=ConnectionOut)
async def update_connection(conn_id: str, data: ConnectionUpdate, user: dict = Depends(get_current_user)):
    async with get_app_connection() as conn:
        row = await conn.fetchrow(
            "SELECT id, is_demo FROM user_db_connections WHERE id = $1::uuid AND user_id = $2::uuid",
            conn_id, user["id"],
        )
        if not row:
            raise HTTPException(status_code=404, detail="Connection not found")

        updates, values = [], []
        if data.name is not None:
            updates.append(f"name = ${len(values) + 1}")
            values.append(data.name)
        if data.is_active is not None:
            updates.append(f"is_active = ${len(values) + 1}")
            values.append(data.is_active)

        if not updates:
            raise HTTPException(status_code=400, detail="Nothing to update")

        values.extend([conn_id, user["id"]])
        updated = await conn.fetchrow(
            f"""UPDATE user_db_connections SET {', '.join(updates)}
                WHERE id = ${len(values) - 1}::uuid AND user_id = ${len(values)}::uuid
                RETURNING id::text, name, db_type, is_demo, is_active, created_at::text""",
            *values,
        )
    return dict(updated)


@router.delete("/{conn_id}", status_code=204)
async def delete_connection(conn_id: str, user: dict = Depends(get_current_user)):
    async with get_app_connection() as conn:
        row = await conn.fetchrow(
            "SELECT is_demo FROM user_db_connections WHERE id = $1::uuid AND user_id = $2::uuid",
            conn_id, user["id"],
        )
        if not row:
            raise HTTPException(status_code=404, detail="Connection not found")
        if row["is_demo"]:
            raise HTTPException(status_code=400, detail="Cannot delete the demo connection")
        await conn.execute(
            "DELETE FROM user_db_connections WHERE id = $1::uuid AND user_id = $2::uuid",
            conn_id, user["id"],
        )


@router.post("/{conn_id}/test")
async def test_conn(conn_id: str, user: dict = Depends(get_current_user)):
    async with get_app_connection() as conn:
        row = await conn.fetchrow(
            "SELECT connection_string, is_demo FROM user_db_connections WHERE id = $1::uuid AND user_id = $2::uuid",
            conn_id, user["id"],
        )
    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")
    if row["is_demo"]:
        return {"status": "ok", "message": "Demo database is always available"}

    conn_str = decrypt_conn_str(row["connection_string"])
    ok, err = await test_connection(conn_str)
    if ok:
        return {"status": "ok", "message": "Connection successful"}
    return {"status": "error", "message": err}
