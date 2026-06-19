import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

import asyncpg

from backend.db.connection import get_analyst_connection
from backend.config import settings

logger = logging.getLogger(__name__)


class QueryExecutionError(Exception):
    def __init__(self, message: str, original: Exception | None = None):
        super().__init__(message)
        self.original = original


class SQLValidationError(QueryExecutionError):
    pass


@asynccontextmanager
async def _get_conn(analyst_dsn: Optional[str] = None):
    """Yield a connection from the shared pool or a one-shot custom connection."""
    if analyst_dsn is None:
        async with get_analyst_connection() as conn:
            yield conn
    else:
        conn = await asyncpg.connect(analyst_dsn)
        try:
            yield conn
        finally:
            await conn.close()


async def validate_sql(sql: str, analyst_dsn: Optional[str] = None) -> tuple[bool, str]:
    """Run EXPLAIN on the SQL without executing it. Returns (is_valid, error_message)."""
    try:
        async with _get_conn(analyst_dsn) as conn:
            await conn.execute(f"EXPLAIN {sql}")
        return True, ""
    except asyncpg.PostgresSyntaxError as e:
        return False, str(e)
    except asyncpg.UndefinedTableError as e:
        return False, f"Table does not exist: {e}"
    except asyncpg.UndefinedColumnError as e:
        return False, f"Column does not exist: {e}"
    except asyncpg.PostgresError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected validation error: {e}"


async def execute_query(
    sql: str,
    analyst_dsn: Optional[str] = None,
) -> tuple[list[dict[str, Any]], list[str], int]:
    """
    Execute a SELECT query and return (rows, column_names, execution_time_ms).
    Rows are capped at settings.max_query_rows.
    """
    if not sql.strip().upper().startswith("SELECT"):
        raise QueryExecutionError("Only SELECT statements are permitted.")

    start = time.monotonic()
    try:
        async with _get_conn(analyst_dsn) as conn:
            try:
                await conn.set_type_codec(
                    "jsonb",
                    encoder=str,
                    decoder=lambda s: s,
                    schema="pg_catalog",
                    format="text",
                )
            except Exception:
                pass

            capped_sql = _apply_row_cap(sql, settings.max_query_rows)
            rows = await conn.fetch(capped_sql)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            if not rows:
                return [], [], elapsed_ms

            columns = list(rows[0].keys())
            result = []
            for row in rows:
                record: dict[str, Any] = {}
                for col in columns:
                    val = row[col]
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    elif isinstance(val, memoryview):
                        val = bytes(val).hex()
                    record[col] = val
                result.append(record)

            return result, columns, elapsed_ms

    except QueryExecutionError:
        raise
    except asyncpg.PostgresSyntaxError as e:
        raise QueryExecutionError(f"SQL syntax error: {e}", e)
    except asyncpg.UndefinedTableError as e:
        raise QueryExecutionError(f"Table not found: {e}", e)
    except asyncpg.UndefinedColumnError as e:
        raise QueryExecutionError(f"Column not found: {e}", e)
    except asyncpg.PostgresError as e:
        raise QueryExecutionError(f"Database error: {e}", e)
    except Exception as e:
        raise QueryExecutionError(f"Query execution failed: {e}", e)


def _apply_row_cap(sql: str, limit: int) -> str:
    stripped = sql.rstrip("; \n\t")
    if "LIMIT" in stripped.upper():
        return stripped
    return f"{stripped}\nLIMIT {limit}"


async def get_table_sample(table_name: str, n: int = 5, analyst_dsn: Optional[str] = None) -> list[dict[str, Any]]:
    safe_name = "".join(c for c in table_name if c.isalnum() or c == "_")
    rows, _, _ = await execute_query(f'SELECT * FROM "{safe_name}" LIMIT {n}', analyst_dsn)
    return rows
