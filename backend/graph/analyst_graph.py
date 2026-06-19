import logging
import time
from typing import Any, Literal, Optional

from langgraph.graph import StateGraph, END, START
from typing_extensions import TypedDict

from backend.agents.schema_agent import run_schema_agent
from backend.agents.sql_agent import run_sql_agent
from backend.agents.validation_agent import run_validation_agent, run_fix_agent
from backend.agents.insight_agent import run_insight_agent
from backend.agents.chart_agent import run_chart_agent
from backend.tools.db_tool import execute_query, QueryExecutionError
from backend.config import settings

logger = logging.getLogger(__name__)


class AnalystState(TypedDict):
    session_id: str
    question: str
    conversation_history: list
    schema_context: str
    generated_sql: str
    sql_valid: bool
    sql_error: str
    query_results: list
    result_columns: list
    chart_type: str
    chart_config: dict
    insight: str
    retry_count: int
    error: str
    execution_time_ms: int
    final_response: dict
    analyst_dsn: Optional[str]   # None → use shared pool; set → use user's DB


async def node_load_schema(state: AnalystState) -> AnalystState:
    return await run_schema_agent(state)


async def node_generate_sql(state: AnalystState) -> AnalystState:
    if state.get("error"):
        return state
    return await run_sql_agent(state)


async def node_validate_sql(state: AnalystState) -> AnalystState:
    if state.get("error"):
        return state
    return await run_validation_agent(state)


async def node_fix_sql(state: AnalystState) -> AnalystState:
    return await run_fix_agent(state)


async def node_execute_query(state: AnalystState) -> AnalystState:
    if state.get("error"):
        return state
    try:
        rows, columns, elapsed_ms = await execute_query(
            state["generated_sql"],
            analyst_dsn=state.get("analyst_dsn"),
        )
        return {**state, "query_results": rows, "result_columns": columns, "execution_time_ms": elapsed_ms}
    except QueryExecutionError as e:
        logger.error(f"Query execution failed: {e}")
        return {**state, "query_results": [], "result_columns": [], "error": str(e)}
    except Exception as e:
        logger.exception("Unexpected error in execute_query node")
        return {**state, "query_results": [], "result_columns": [], "error": f"Query failed: {e}"}


async def node_select_chart(state: AnalystState) -> AnalystState:
    if state.get("error"):
        return state
    return await run_chart_agent(state)


async def node_generate_insight(state: AnalystState) -> AnalystState:
    if state.get("error"):
        return state
    return await run_insight_agent(state)


async def node_build_response(state: AnalystState) -> AnalystState:
    error = state.get("error", "")
    if not error and not state.get("sql_valid", False) and state.get("generated_sql"):
        error = f"Could not generate valid SQL after {settings.max_retry_count} attempts. {state.get('sql_error', '')}"

    if error:
        final = {
            "question": state.get("question", ""),
            "sql": state.get("generated_sql", ""),
            "results": [],
            "columns": [],
            "chart_type": "table",
            "chart_config": {},
            "insight": "I couldn't answer that question. Try rephrasing it or check the schema explorer to see what data is available.",
            "execution_time_ms": state.get("execution_time_ms", 0),
            "error": error,
            "row_count": 0,
        }
    else:
        results = state.get("query_results", [])
        final = {
            "question": state.get("question", ""),
            "sql": state.get("generated_sql", ""),
            "results": results,
            "columns": state.get("result_columns", []),
            "chart_type": state.get("chart_type", "table"),
            "chart_config": state.get("chart_config", {}),
            "insight": state.get("insight", ""),
            "execution_time_ms": state.get("execution_time_ms", 0),
            "error": None,
            "row_count": len(results),
        }

    return {**state, "final_response": final}


def route_after_validation(state: AnalystState) -> Literal["execute_query", "fix_sql", "build_response"]:
    if state.get("error"):
        return "build_response"
    if state.get("sql_valid", False):
        return "execute_query"
    if state.get("retry_count", 0) >= settings.max_retry_count:
        return "build_response"
    return "fix_sql"


def build_analyst_graph() -> StateGraph:
    graph = StateGraph(AnalystState)

    graph.add_node("load_schema", node_load_schema)
    graph.add_node("generate_sql", node_generate_sql)
    graph.add_node("validate_sql", node_validate_sql)
    graph.add_node("fix_sql", node_fix_sql)
    graph.add_node("execute_query", node_execute_query)
    graph.add_node("select_chart", node_select_chart)
    graph.add_node("generate_insight", node_generate_insight)
    graph.add_node("build_response", node_build_response)

    graph.add_edge(START, "load_schema")
    graph.add_edge("load_schema", "generate_sql")
    graph.add_edge("generate_sql", "validate_sql")
    graph.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {"execute_query": "execute_query", "fix_sql": "fix_sql", "build_response": "build_response"},
    )
    graph.add_edge("fix_sql", "validate_sql")
    graph.add_edge("execute_query", "select_chart")
    graph.add_edge("select_chart", "generate_insight")
    graph.add_edge("generate_insight", "build_response")
    graph.add_edge("build_response", END)

    return graph.compile()


_compiled_graph = None


def get_analyst_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_analyst_graph()
    return _compiled_graph


async def run_analyst(
    session_id: str,
    question: str,
    conversation_history: list,
    analyst_dsn: Optional[str] = None,
) -> dict[str, Any]:
    graph = get_analyst_graph()

    initial_state: AnalystState = {
        "session_id": session_id,
        "question": question,
        "conversation_history": conversation_history,
        "schema_context": "",
        "generated_sql": "",
        "sql_valid": False,
        "sql_error": "",
        "query_results": [],
        "result_columns": [],
        "chart_type": "table",
        "chart_config": {},
        "insight": "",
        "retry_count": 0,
        "error": "",
        "execution_time_ms": 0,
        "final_response": {},
        "analyst_dsn": analyst_dsn,
    }

    try:
        final_state = await graph.ainvoke(initial_state)
        return final_state.get("final_response", {})
    except Exception as e:
        logger.exception("Analyst graph invocation failed")
        return {
            "question": question,
            "sql": "",
            "results": [],
            "columns": [],
            "chart_type": "table",
            "chart_config": {},
            "insight": "I couldn't answer that question. Try rephrasing it or check the schema explorer.",
            "execution_time_ms": 0,
            "error": str(e),
            "row_count": 0,
        }
