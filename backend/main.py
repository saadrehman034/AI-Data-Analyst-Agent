import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.db.connection import (
    create_app_pool, create_analyst_pool, close_pools,
    check_app_db_health, check_analyst_db_health, get_app_connection,
)
from backend.graph.analyst_graph import run_analyst
from backend.tools.schema_tool import get_schema_for_api, invalidate_schema_cache
from backend.memory.conversation_memory import (
    add_to_history, get_recent_history, get_history, clear_history, prune_expired_sessions,
)
from backend.auth.routes import router as auth_router
from backend.auth.dependencies import get_current_user, get_optional_user
from backend.connections.routes import router as connections_router
from backend.tools.connection_tool import resolve_connection_string

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rate limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

SUGGESTED_QUESTIONS = [
    "What are the top 10 best-selling products by revenue?",
    "Show me monthly revenue for the past 12 months",
    "Which product categories generate the most profit?",
    "What percentage of orders were cancelled last year?",
    "Who are our top 10 customers by total spend?",
    "What is the average order value by country?",
    "How many new customers signed up each month this year?",
    "What is the average customer satisfaction score by support ticket category?",
]


async def _ensure_app_schema(conn):
    """Create all querymind app tables if they don't exist yet."""
    await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_db_connections (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            db_type VARCHAR(50) NOT NULL DEFAULT 'postgresql',
            connection_string TEXT NOT NULL,
            is_demo BOOLEAN NOT NULL DEFAULT FALSE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_db_connections_user_id ON user_db_connections(user_id)"
    )
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS query_sessions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            session_id UUID NOT NULL REFERENCES query_sessions(id) ON DELETE CASCADE,
            question TEXT NOT NULL,
            generated_sql TEXT,
            result_row_count INTEGER,
            chart_type VARCHAR(20),
            insight TEXT,
            execution_time_ms INTEGER,
            had_error BOOLEAN NOT NULL DEFAULT FALSE,
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_query_history_session_id ON query_history(session_id)"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at DESC)"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting QueryMind API [{settings.environment}]...")
    await create_app_pool()
    await create_analyst_pool()
    async with get_app_connection() as conn:
        await _ensure_app_schema(conn)
    logger.info("Database pools and schema initialised")
    yield
    logger.info("Shutting down QueryMind API...")
    await close_pools()


app = FastAPI(
    title="QueryMind API",
    description="AI Data Analyst Agent — query your database in plain English",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

# ── Rate limiting middleware ──────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "https://ai-data-analyst-lilac.vercel.app",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security headers middleware ───────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# ── Request logging middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.debug(f"{request.method} {request.url.path} → {response.status_code}")
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(connections_router)


# ── Request / Response models ─────────────────────────────────────────────────
class QueryRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str = Field(min_length=1, max_length=2000)
    connection_id: Optional[str] = None   # which DB to query; None → user's default


class QueryResponse(BaseModel):
    session_id: str
    question: str
    sql: str
    results: list[dict[str, Any]]
    columns: list[str]
    chart_type: str
    chart_config: dict[str, Any]
    insight: str
    execution_time_ms: int
    row_count: int
    error: str | None


# ── Routes ────────────────────────────────────────────────────────────────────
@app.post("/query", response_model=QueryResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def query(
    request: Request,          # required by slowapi
    req: QueryRequest,
    user: Optional[dict] = Depends(get_optional_user),
):
    session_id = req.session_id or str(uuid.uuid4())
    conversation_history = get_recent_history(session_id)

    # Determine which analyst DB to use
    analyst_dsn: Optional[str] = None
    if user and req.connection_id:
        analyst_dsn = await resolve_connection_string(user["id"], req.connection_id)
    elif user:
        analyst_dsn = await resolve_connection_string(user["id"])

    try:
        result = await run_analyst(
            session_id=session_id,
            question=req.question,
            conversation_history=conversation_history,
            analyst_dsn=analyst_dsn,
        )
    except Exception as e:
        logger.exception("Analyst graph crashed")
        raise HTTPException(status_code=500, detail=str(e))

    user_id = user["id"] if user else None
    if not result.get("error"):
        add_to_history(
            session_id=session_id,
            question=req.question,
            generated_sql=result.get("sql", ""),
            insight=result.get("insight", ""),
            chart_type=result.get("chart_type", "table"),
        )
        await _persist_query(session_id, user_id, req.question, result, had_error=False)
    else:
        await _persist_query(session_id, user_id, req.question, result, had_error=True)

    prune_expired_sessions()
    return QueryResponse(
        session_id=session_id,
        question=req.question,
        sql=result.get("sql", ""),
        results=result.get("results", []),
        columns=result.get("columns", []),
        chart_type=result.get("chart_type", "table"),
        chart_config=result.get("chart_config", {}),
        insight=result.get("insight", ""),
        execution_time_ms=result.get("execution_time_ms", 0),
        row_count=result.get("row_count", 0),
        error=result.get("error"),
    )


@app.get("/schema")
async def get_schema(
    request: Request,
    connection_id: Optional[str] = None,
    user: Optional[dict] = Depends(get_optional_user),
):
    try:
        analyst_dsn: Optional[str] = None
        if user and connection_id:
            analyst_dsn = await resolve_connection_string(user["id"], connection_id)
        elif user:
            analyst_dsn = await resolve_connection_string(user["id"])
        tables = await get_schema_for_api(analyst_dsn=analyst_dsn)
        return {"tables": tables}
    except Exception as e:
        logger.exception("Schema endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{session_id}")
async def get_session_history(session_id: str):
    try:
        history = get_history(session_id)
        db_history = await _load_db_history(session_id)
        return {"session_id": session_id, "entries": _merge_history(history, db_history)}
    except Exception as e:
        logger.exception("History endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history/{session_id}")
async def delete_session_history(session_id: str):
    clear_history(session_id)
    try:
        async with get_app_connection() as conn:
            await conn.execute(
                "DELETE FROM query_sessions WHERE id = $1::uuid", session_id
            )
    except Exception as e:
        logger.warning(f"Could not delete DB history for {session_id}: {e}")
    return {"status": "cleared", "session_id": session_id}


@app.get("/suggested-questions")
async def suggested_questions():
    return {"questions": SUGGESTED_QUESTIONS}


@app.get("/health")
async def health():
    app_ok = await check_app_db_health()
    analyst_ok = await check_analyst_db_health()
    llm_ok = bool(settings.gemini_api_key and len(settings.gemini_api_key) > 10)
    status = "ok" if (app_ok and analyst_ok and llm_ok) else "degraded"
    return {
        "status": status,
        "version": "2.0.0",
        "environment": settings.environment,
        "db": "connected" if app_ok else "error",
        "analyst_db": "connected" if analyst_ok else "error",
        "llm": "connected" if llm_ok else "error",
    }


# ── Internal helpers ──────────────────────────────────────────────────────────
async def _persist_query(
    session_id: str,
    user_id: Optional[str],
    question: str,
    result: dict,
    had_error: bool,
):
    try:
        async with get_app_connection() as conn:
            await conn.execute(
                """INSERT INTO query_sessions (id, user_id)
                   VALUES ($1::uuid, $2::uuid)
                   ON CONFLICT (id) DO UPDATE SET last_active_at = NOW()""",
                session_id, user_id,
            )
            await conn.execute(
                """INSERT INTO query_history
                   (session_id, question, generated_sql, result_row_count,
                    chart_type, insight, execution_time_ms, had_error, error_message)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9)""",
                session_id, question,
                result.get("sql", ""),
                result.get("row_count", 0),
                result.get("chart_type", "table"),
                result.get("insight", ""),
                result.get("execution_time_ms", 0),
                had_error,
                result.get("error") if had_error else None,
            )
    except Exception as e:
        logger.warning(f"Could not persist query history: {e}")


async def _load_db_history(session_id: str) -> list[dict]:
    try:
        async with get_app_connection() as conn:
            rows = await conn.fetch(
                """SELECT question, generated_sql, result_row_count, chart_type,
                          insight, execution_time_ms, had_error, created_at
                   FROM query_history
                   WHERE session_id = $1::uuid
                   ORDER BY created_at ASC""",
                session_id,
            )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"Could not load DB history: {e}")
        return []


def _merge_history(in_memory: list[dict], from_db: list[dict]) -> list[dict]:
    if from_db:
        return [
            {
                "question": r.get("question", ""),
                "sql": r.get("generated_sql", ""),
                "insight": r.get("insight", ""),
                "chart_type": r.get("chart_type", "table"),
                "row_count": r.get("result_row_count", 0),
                "execution_time_ms": r.get("execution_time_ms", 0),
                "had_error": r.get("had_error", False),
                "timestamp": r["created_at"].isoformat()
                if hasattr(r.get("created_at"), "isoformat")
                else str(r.get("created_at", "")),
            }
            for r in from_db
        ]
    return in_memory
