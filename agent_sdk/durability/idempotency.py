"""Idempotency key tracking to prevent duplicate tool executions."""

from __future__ import annotations

import json
import logging
from typing import Any, TYPE_CHECKING

from agent_sdk.isolation.scope import get_user_scope

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection

logger = logging.getLogger("agent_sdk.durability.idempotency")


class IdempotencyTracker:
    """Tracks idempotency keys so tool calls are not duplicated on resume."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    async def record(self, key: str, result: Any, session_id: str) -> None:
        """Record that a key has been executed with a given result."""
        user_id = get_user_scope()
        result_json = json.dumps(result if isinstance(result, dict) else {"output": result}, default=str)
        sql = (
            "INSERT OR IGNORE INTO idempotency_keys (key, session_id, user_id, result) "
            "VALUES (?, ?, ?, ?)"
        )
        await self._db.execute(sql, [key, session_id, user_id, result_json])
        logger.debug("Recorded idempotency key: %s", key)

    async def check(self, key: str) -> dict[str, Any] | None:
        """Return cached result if this key was already executed, else None."""
        user_id = get_user_scope()
        row = await self._db.fetch_one(
            "SELECT result FROM idempotency_keys WHERE key = ? AND user_id = ?",
            [key, user_id],
        )
        if row:
            try:
                return json.loads(row["result"])  # type: ignore[no-any-return]
            except (json.JSONDecodeError, TypeError):
                return {"output": row["result"]}
        return None

    async def clear(self, session_id: str) -> None:
        """Remove all idempotency keys for a session."""
        user_id = get_user_scope()
        await self._db.execute(
            "DELETE FROM idempotency_keys WHERE session_id = ? AND user_id = ?",
            [session_id, user_id],
        )
        logger.debug("Cleared idempotency keys for session %s", session_id)
