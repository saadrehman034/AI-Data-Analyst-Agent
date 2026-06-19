import asyncio
import logging
from typing import Any

import google.generativeai as genai

from backend.config import settings

logger = logging.getLogger(__name__)
_model: genai.GenerativeModel | None = None


def _get_model() -> genai.GenerativeModel:
    global _model
    if _model is None:
        genai.configure(api_key=settings.gemini_api_key, transport="rest")
        _model = genai.GenerativeModel(settings.gemini_model)
    return _model


def _format_conversation_history(history: list[dict]) -> str:
    if not history:
        return "No prior conversation."
    lines = []
    for entry in history[-settings.conversation_history_limit:]:
        lines.append(f"User: {entry.get('question', '')}")
        if entry.get("insight"):
            lines.append(f"Assistant insight: {entry.get('insight', '')}")
        if entry.get("generated_sql"):
            lines.append(f"SQL used: {entry.get('generated_sql', '')}")
    return "\n".join(lines)


async def run_sql_agent(state: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a PostgreSQL SELECT query from the user's natural language question.
    Uses conversation history for context so follow-up questions resolve correctly.
    """
    try:
        history_text = _format_conversation_history(state.get("conversation_history", []))
        prompt = f"""You are an expert PostgreSQL analyst. You write clean, efficient, correct SQL queries.
You always use proper JOINs. You never use SELECT *.
You always alias columns with readable names.
You always add appropriate WHERE clauses to avoid returning massive datasets.
You never write DELETE, UPDATE, INSERT, or DROP statements — read only.
When asked about time periods like "last month" or "this year" use NOW() and INTERVAL.
Always LIMIT results to 100 rows unless the user asks for totals or aggregates.
CRITICAL: order_items.discount_percent is stored as 0–100 (e.g. 25 = 25%). Always divide by 100.0 when computing.
Revenue = quantity * unit_price * (1 - discount_percent/100.0)
Profit = Revenue - (quantity * products.cost)

Database schema:
{state.get("schema_context", "")}

Conversation history:
{history_text}

User question: {state.get('question', '')}

Write a single PostgreSQL SELECT query that answers this question.
Return only the SQL query. No explanation. No markdown. No backticks."""

        model = _get_model()
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0, max_output_tokens=1000),
        )

        sql = response.text.strip()
        sql = _clean_sql(sql)
        logger.info(f"Generated SQL: {sql[:200]}...")
        return {**state, "generated_sql": sql, "sql_error": ""}

    except Exception as e:
        logger.exception("SQL agent failed")
        return {**state, "generated_sql": "", "error": f"Failed to generate SQL: {e}"}


def _clean_sql(sql: str) -> str:
    if sql.startswith("```"):
        lines = sql.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        sql = "\n".join(lines).strip()
    return sql.strip().rstrip(";")
