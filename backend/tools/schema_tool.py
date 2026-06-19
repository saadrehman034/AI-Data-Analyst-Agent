import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Optional

import asyncpg

from backend.db.connection import get_analyst_connection

logger = logging.getLogger(__name__)

# Global cache for the default analyst DB (per-connection caches use _dynamic_caches)
_schema_cache: Optional["SchemaCache"] = None
_dynamic_caches: dict[str, "SchemaCache"] = {}   # keyed by analyst_dsn
_cache_ttl_seconds: int = 300


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    column_default: Optional[str]


@dataclass
class ForeignKeyInfo:
    column: str
    references_table: str
    references_column: str


@dataclass
class TableInfo:
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)
    row_count: int = 0


@dataclass
class SchemaCache:
    tables: dict[str, TableInfo]
    cached_at: float
    formatted_context: str


# ── Column-level hints passed to the LLM ─────────────────────────────────────
_COLUMN_HINTS: dict[tuple[str, str], str] = {
    ("order_items", "discount_percent"): "stored as 0–100 integer (e.g. 25 = 25%); divide by 100.0 in calculations",
    ("order_items", "unit_price"): "price per unit charged at time of order (may differ from products.price)",
    ("order_items", "quantity"): "number of units ordered",
    ("products", "cost"): "unit cost to source/produce the product",
    ("products", "price"): "retail list price before discounts",
    ("orders", "total_amount"): "pre-computed order total after discounts; use SUM(total_amount) for revenue",
    ("customers", "customer_segment"): "one of: 'new', 'returning', 'vip'",
    ("support_tickets", "satisfaction_score"): "integer 1–5 (5 = most satisfied); NULL when ticket is open",
    ("support_tickets", "status"): "one of: 'open', 'closed'",
}


@asynccontextmanager
async def _any_connection(analyst_dsn: Optional[str]):
    """Yield a connection: uses the shared pool for the default DB, or a one-shot for custom DBs."""
    if analyst_dsn is None:
        async with get_analyst_connection() as conn:
            yield conn
    else:
        conn = await asyncpg.connect(analyst_dsn)
        try:
            yield conn
        finally:
            await conn.close()


async def _fetch_schema_from_conn(conn) -> dict[str, TableInfo]:
    column_rows = await conn.fetch("""
        SELECT c.table_name, c.column_name, c.data_type, c.is_nullable, c.column_default
        FROM information_schema.columns c
        JOIN information_schema.tables t
            ON c.table_name = t.table_name AND c.table_schema = t.table_schema
        WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'
        ORDER BY c.table_name, c.ordinal_position
    """)
    fk_rows = await conn.fetch("""
        SELECT kcu.table_name, kcu.column_name,
               ccu.table_name AS references_table,
               ccu.column_name AS references_column
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
    """)
    table_rows = await conn.fetch("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)

    tables: dict[str, TableInfo] = {r["table_name"]: TableInfo(name=r["table_name"]) for r in table_rows}

    for row in column_rows:
        tname = row["table_name"]
        if tname in tables:
            tables[tname].columns.append(ColumnInfo(
                name=row["column_name"],
                data_type=row["data_type"],
                is_nullable=row["is_nullable"] == "YES",
                column_default=row["column_default"],
            ))

    for row in fk_rows:
        tname = row["table_name"]
        if tname in tables:
            tables[tname].foreign_keys.append(ForeignKeyInfo(
                column=row["column_name"],
                references_table=row["references_table"],
                references_column=row["references_column"],
            ))

    for tname in tables:
        try:
            tables[tname].row_count = await conn.fetchval(f'SELECT COUNT(*) FROM "{tname}"')
        except Exception as e:
            logger.warning(f"Could not get row count for {tname}: {e}")

    return tables


async def load_schema(analyst_dsn: Optional[str] = None) -> SchemaCache:
    global _schema_cache, _dynamic_caches
    now = time.time()

    if analyst_dsn is None:
        if _schema_cache and (now - _schema_cache.cached_at) < _cache_ttl_seconds:
            return _schema_cache
    else:
        cached = _dynamic_caches.get(analyst_dsn)
        if cached and (now - cached.cached_at) < _cache_ttl_seconds:
            return cached

    logger.info(f"Loading schema from {'custom DSN' if analyst_dsn else 'default analyst DB'}...")
    async with _any_connection(analyst_dsn) as conn:
        tables = await _fetch_schema_from_conn(conn)

    context = format_schema_context(tables)
    cache = SchemaCache(tables=tables, cached_at=time.time(), formatted_context=context)

    if analyst_dsn is None:
        _schema_cache = cache
    else:
        _dynamic_caches[analyst_dsn] = cache

    logger.info(f"Schema loaded: {len(tables)} tables")
    return cache


def format_schema_context(tables: dict[str, TableInfo]) -> str:
    lines = [
        "DATABASE SCHEMA",
        "=" * 60,
        "IMPORTANT: discount_percent is stored as 0–100 (e.g. 25 means 25%); always divide by 100.0 when computing revenue or profit.",
        "Profit formula: SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0) - oi.quantity * p.cost)",
    ]
    for tname, tinfo in sorted(tables.items()):
        lines.append(f"\nTable: {tname} ({tinfo.row_count:,} rows)")
        lines.append("Columns:")
        for col in tinfo.columns:
            nullable = "nullable" if col.is_nullable else "not null"
            hint = _COLUMN_HINTS.get((tname, col.name), "")
            suffix = f"  — {hint}" if hint else ""
            lines.append(f"  - {col.name}: {col.data_type} ({nullable}){suffix}")
        if tinfo.foreign_keys:
            lines.append("Foreign Keys:")
            for fk in tinfo.foreign_keys:
                lines.append(f"  - {fk.column} → {fk.references_table}.{fk.references_column}")
    return "\n".join(lines)


def get_cached_schema() -> Optional[SchemaCache]:
    return _schema_cache


def invalidate_schema_cache(analyst_dsn: Optional[str] = None):
    global _schema_cache, _dynamic_caches
    if analyst_dsn is None:
        _schema_cache = None
    else:
        _dynamic_caches.pop(analyst_dsn, None)


async def get_schema_for_api(analyst_dsn: Optional[str] = None) -> list[dict]:
    cache = await load_schema(analyst_dsn)
    return [
        {
            "name": tname,
            "row_count": tinfo.row_count,
            "columns": [{"name": col.name, "type": col.data_type} for col in tinfo.columns],
        }
        for tname, tinfo in sorted(cache.tables.items())
    ]
