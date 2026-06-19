import asyncio
import logging
from typing import Any

import google.generativeai as genai

from backend.tools.db_tool import validate_sql
from backend.config import settings

logger = logging.getLogger(__name__)
_model: genai.GenerativeModel | None = None


def _get_model() -> genai.GenerativeModel:
    global _model
    if _model is None:
        genai.configure(api_key=settings.gemini_api_key, transport="rest")
        _model = genai.GenerativeModel(settings.gemini_model)
    return _model


async def run_validation_agent(state: dict[str, Any]) -> dict[str, Any]:
    """
    Run EXPLAIN on the generated SQL. Sets sql_valid and sql_error in state.
    Does not execute the query — safe for read-path validation.
    """
    sql = state.get("generated_sql", "").strip()
    if not sql:
        return {**state, "sql_valid": False, "sql_error": "No SQL was generated."}

    try:
        is_valid, error_message = await validate_sql(sql, analyst_dsn=state.get("analyst_dsn"))
        return {**state, "sql_valid": is_valid, "sql_error": error_message}
    except Exception as e:
        logger.exception("Validation agent failed")
        return {**state, "sql_valid": False, "sql_error": str(e)}


async def run_fix_agent(state: dict[str, Any]) -> dict[str, Any]:
    """
    Ask Gemini to fix the broken SQL given the original question, the bad SQL,
    the error message, and the schema context.
    """
    try:
        retry_count = state.get("retry_count", 0) + 1

        prompt = f"""You are an expert PostgreSQL debugger.

The following SQL query failed with an error.
Original question: {state.get('question', '')}
Bad SQL: {state.get('generated_sql', '')}
Error: {state.get('sql_error', '')}
Schema: {state.get('schema_context', '')}

Fix the SQL query so it runs correctly.
Return only the corrected SQL. No explanation. No markdown. No backticks."""

        model = _get_model()
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0, max_output_tokens=1000),
        )

        fixed_sql = response.text.strip()
        if fixed_sql.startswith("```"):
            lines = fixed_sql.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            fixed_sql = "\n".join(lines).strip()
        fixed_sql = fixed_sql.rstrip(";")

        logger.info(f"Fixed SQL (attempt {retry_count}): {fixed_sql[:200]}...")
        return {**state, "generated_sql": fixed_sql, "retry_count": retry_count, "sql_error": ""}

    except Exception as e:
        logger.exception("Fix agent failed")
        return {
            **state,
            "retry_count": state.get("retry_count", 0) + 1,
            "error": f"SQL fix failed: {e}",
        }
