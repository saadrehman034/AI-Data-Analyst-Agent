import asyncio
import json
import logging
from typing import Any

import google.generativeai as genai

from backend.config import settings

logger = logging.getLogger(__name__)
_model: genai.GenerativeModel | None = None


def _get_model() -> genai.GenerativeModel:
    global _model
    if _model is None:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(settings.gemini_model)
    return _model


async def run_insight_agent(state: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a plain English explanation of the query results.
    Reads results, highlights the most important finding in 2-3 sentences.
    """
    try:
        results = state.get("query_results", [])
        row_count = len(results)
        sample = results[:10]

        try:
            sample_text = json.dumps(sample, indent=2, default=str)
        except Exception:
            sample_text = str(sample)[:2000]

        prompt = f"""You are a senior business analyst. You explain data findings clearly to non-technical people.
You never say "the query shows" or "the data indicates" — just say what the finding is directly.
You highlight the single most important number or trend.
You keep it to 2-3 sentences maximum.
You sound like a smart human, not a robot.

Question asked: {state.get('question', '')}
SQL run: {state.get('generated_sql', '')}
Results (first 10 rows): {sample_text}
Total rows returned: {row_count}

Write a plain English insight explaining what this data shows."""

        model = _get_model()
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.3, max_output_tokens=300),
        )

        insight = response.text.strip()
        logger.info(f"Generated insight: {insight[:100]}...")
        return {**state, "insight": insight}

    except Exception as e:
        logger.exception("Insight agent failed")
        return {**state, "insight": "Results retrieved successfully. See the chart and table below for details."}
