import logging
from typing import Any

from backend.tools.schema_tool import load_schema

logger = logging.getLogger(__name__)


async def run_schema_agent(state: dict[str, Any]) -> dict[str, Any]:
    try:
        analyst_dsn = state.get("analyst_dsn")
        cache = await load_schema(analyst_dsn=analyst_dsn)
        return {**state, "schema_context": cache.formatted_context}
    except Exception as e:
        logger.exception("Schema agent failed")
        return {**state, "schema_context": "", "error": f"Failed to load database schema: {e}"}
