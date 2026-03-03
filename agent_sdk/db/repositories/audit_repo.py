"""Repository for audit_log table access."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from agent_sdk.isolation.scope import get_user_scope

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection


class AuditRepository:
    """Append-only audit log, scoped by user_id."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    async def create(
        self,
        action: str,
        details: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Write an audit log entry."""
        user_id = get_user_scope()
        entry_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        sql = (
            "INSERT INTO audit_log (id, timestamp, user_id, session_id, action, details) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        )
        params = [entry_id, now, user_id, session_id, action, json.dumps(details or {})]
        await self._db.execute(sql, params)
        return {
            "id": entry_id,
            "timestamp": now,
            "user_id": user_id,
            "session_id": session_id,
            "action": action,
            "details": details or {},
        }

    async def query(
        self,
        user_id: str | None = None,
        action: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query audit log entries with optional filters."""
        uid = user_id or get_user_scope()
        conditions = ["user_id = ?"]
        params: list[Any] = [uid]

        if action:
            conditions.append("action = ?")
            params.append(action)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)

        sql = (
            f"SELECT * FROM audit_log WHERE {' AND '.join(conditions)} "
            f"ORDER BY timestamp DESC LIMIT ?"
        )
        params.append(limit)
        return await self._db.fetch_all(sql, params)
