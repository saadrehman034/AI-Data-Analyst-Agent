import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)

_SESSION_TTL_SECONDS = 3600 * 4


@dataclass
class ConversationEntry:
    question: str
    generated_sql: str
    insight: str
    chart_type: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Session:
    entries: list[ConversationEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)


_sessions: dict[str, Session] = defaultdict(Session)


def _touch(session_id: str) -> Session:
    session = _sessions[session_id]
    session.last_active_at = time.time()
    return session


def add_to_history(
    session_id: str,
    question: str,
    generated_sql: str,
    insight: str,
    chart_type: str,
) -> None:
    session = _touch(session_id)
    entry = ConversationEntry(
        question=question,
        generated_sql=generated_sql,
        insight=insight,
        chart_type=chart_type,
    )
    session.entries.append(entry)
    logger.debug(f"Session {session_id}: {len(session.entries)} entries stored")


def get_history(session_id: str) -> list[dict]:
    """Return all entries for the session as a list of dicts."""
    if session_id not in _sessions:
        return []
    session = _touch(session_id)
    return [
        {
            "question": e.question,
            "generated_sql": e.generated_sql,
            "insight": e.insight,
            "chart_type": e.chart_type,
            "timestamp": e.timestamp,
        }
        for e in session.entries
    ]


def get_recent_history(session_id: str) -> list[dict]:
    """Return the last N entries for the LLM prompt context."""
    all_entries = get_history(session_id)
    return all_entries[-settings.conversation_history_limit:]


def clear_history(session_id: str) -> None:
    if session_id in _sessions:
        del _sessions[session_id]
        logger.info(f"Cleared history for session {session_id}")


def get_session_ids() -> list[str]:
    return list(_sessions.keys())


def prune_expired_sessions() -> int:
    now = time.time()
    expired = [
        sid for sid, session in _sessions.items()
        if (now - session.last_active_at) > _SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del _sessions[sid]
    if expired:
        logger.info(f"Pruned {len(expired)} expired sessions")
    return len(expired)


def session_exists(session_id: str) -> bool:
    return session_id in _sessions
