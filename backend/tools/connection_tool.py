import asyncio
import logging
from typing import Optional

import asyncpg
from cryptography.fernet import Fernet

from backend.config import settings

logger = logging.getLogger(__name__)

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.fernet_key
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_conn_str(conn_str: str) -> str:
    return _get_fernet().encrypt(conn_str.encode()).decode()


def decrypt_conn_str(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


async def test_connection(conn_str: str, timeout: float = 8.0) -> tuple[bool, str]:
    try:
        conn = await asyncio.wait_for(asyncpg.connect(conn_str), timeout=timeout)
        await conn.close()
        return True, ""
    except asyncio.TimeoutError:
        return False, "Connection timed out after 8 seconds"
    except asyncpg.InvalidPasswordError:
        return False, "Authentication failed — check username and password"
    except Exception as e:
        return False, str(e)[:300]


async def resolve_connection_string(user_id: str, connection_id: Optional[str] = None) -> str:
    """
    Return the asyncpg DSN for the given user's selected connection.
    Falls back to the demo/analyst DB if none is found.
    """
    from backend.db.connection import get_app_connection

    async with get_app_connection() as conn:
        if connection_id:
            row = await conn.fetchrow(
                """SELECT connection_string, is_demo
                   FROM user_db_connections
                   WHERE id = $1::uuid AND user_id = $2::uuid AND is_active = true""",
                connection_id, user_id,
            )
        else:
            # Use the first active connection (demo preferred so new users see data)
            row = await conn.fetchrow(
                """SELECT connection_string, is_demo
                   FROM user_db_connections
                   WHERE user_id = $1::uuid AND is_active = true
                   ORDER BY is_demo DESC, created_at ASC
                   LIMIT 1""",
                user_id,
            )

    if not row or row["is_demo"]:
        return settings.analyst_db_url

    return decrypt_conn_str(row["connection_string"])


async def get_dynamic_connection(conn_str: str):
    """Context manager that returns an asyncpg connection for any DSN."""
    return await asyncpg.connect(conn_str)
