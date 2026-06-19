import asyncio
import json
import logging
import re
from typing import Any

import google.generativeai as genai

from backend.config import settings

logger = logging.getLogger(__name__)
_model: genai.GenerativeModel | None = None

DATE_LIKE_NAMES = {"date", "month", "year", "week", "quarter", "period", "day", "time", "created_at", "order_date"}
NUMERIC_TYPES = {"integer", "numeric", "real", "double", "bigint", "smallint", "decimal", "float"}


def _get_model() -> genai.GenerativeModel:
    global _model
    if _model is None:
        genai.configure(api_key=settings.gemini_api_key, transport="rest")
        _model = genai.GenerativeModel(
            settings.gemini_model,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0,
                max_output_tokens=200,
            ),
        )
    return _model


def _infer_chart_type_heuristic(columns: list[str], results: list[dict]) -> dict:
    """Fast heuristic chart selection without LLM, used as fallback."""
    if not results or not columns:
        return {"chart_type": "table", "x_axis": None, "y_axis": None, "title": "Results"}

    if len(results) == 1 and len(columns) == 1:
        return {
            "chart_type": "number",
            "x_axis": None,
            "y_axis": columns[0],
            "title": columns[0].replace("_", " ").title(),
        }

    has_date_col = any(c.lower() in DATE_LIKE_NAMES or "date" in c.lower() or "month" in c.lower() for c in columns)
    numeric_cols = []
    text_cols = []
    for col in columns:
        sample_val = results[0].get(col)
        if isinstance(sample_val, (int, float)):
            numeric_cols.append(col)
        elif sample_val is None:
            numeric_cols.append(col)
        else:
            text_cols.append(col)

    if has_date_col and numeric_cols:
        date_col = next((c for c in columns if "date" in c.lower() or "month" in c.lower() or "year" in c.lower() or c.lower() in DATE_LIKE_NAMES), columns[0])
        return {
            "chart_type": "line",
            "x_axis": date_col,
            "y_axis": numeric_cols[0],
            "title": f"{numeric_cols[0].replace('_', ' ').title()} over Time",
        }

    if text_cols and numeric_cols and len(results) <= 8:
        return {
            "chart_type": "bar",
            "x_axis": text_cols[0],
            "y_axis": numeric_cols[0],
            "title": f"{numeric_cols[0].replace('_', ' ').title()} by {text_cols[0].replace('_', ' ').title()}",
        }

    if text_cols and numeric_cols and len(results) <= 6:
        return {
            "chart_type": "pie",
            "x_axis": text_cols[0],
            "y_axis": numeric_cols[0],
            "title": f"{numeric_cols[0].replace('_', ' ').title()} Distribution",
        }

    return {
        "chart_type": "table",
        "x_axis": columns[0] if columns else None,
        "y_axis": columns[1] if len(columns) > 1 else None,
        "title": "Query Results",
    }


async def run_chart_agent(state: dict[str, Any]) -> dict[str, Any]:
    """
    Decide the best chart type for the query results using Gemini.
    Falls back to heuristic selection if the LLM call fails.
    """
    try:
        results = state.get("query_results", [])
        columns = state.get("result_columns", [])
        row_count = len(results)
        sample = results[:5]

        try:
            sample_text = json.dumps(sample, indent=2, default=str)
        except Exception:
            sample_text = str(sample)[:1000]

        prompt = f"""You select the best chart type for a given dataset.
Rules:
- If result is a single number → type: "number"
- If one column is a date/month/year and one is numeric → type: "line"
- If comparing categories (under 8) with one numeric column → type: "bar"
- If showing proportions that add to 100% → type: "pie"
- If multiple columns or more than 8 categories → type: "table"

Columns: {columns}
Row count: {row_count}
Sample data: {sample_text}

Return JSON only:
{{"chart_type": "bar|line|pie|number|table", "x_axis": "column_name_or_null", "y_axis": "column_name_or_null", "title": "chart title"}}"""

        model = _get_model()
        response = await asyncio.to_thread(model.generate_content, prompt)

        raw = response.text.strip()
        # Strip markdown fences if Gemini wraps the JSON
        raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("```").strip()
        chart_config = json.loads(raw)

        valid_types = {"bar", "line", "pie", "number", "table"}
        if chart_config.get("chart_type") not in valid_types:
            chart_config["chart_type"] = "table"

        logger.info(f"Chart type selected: {chart_config.get('chart_type')}")
        return {
            **state,
            "chart_type": chart_config.get("chart_type", "table"),
            "chart_config": chart_config,
        }

    except Exception as e:
        logger.warning(f"Chart agent LLM failed, using heuristic: {e}")
        heuristic = _infer_chart_type_heuristic(
            state.get("result_columns", []),
            state.get("query_results", []),
        )
        return {
            **state,
            "chart_type": heuristic["chart_type"],
            "chart_config": heuristic,
        }
