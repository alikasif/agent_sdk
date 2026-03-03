"""Repository for sessions table access."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from agent_sdk.isolation.filter import ScopedQueryBuilder

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection


class SessionRepository:
    """CRUD operations for the sessions table, scoped by user_id."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self._qb = ScopedQueryBuilder()

    async def create(
        self,
        agent_name: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new session and return its row."""
        sid = session_id or uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        values: dict[str, Any] = {
            "id": sid,
            "agent_name": agent_name,
            "status": "active",
            "metadata": json.dumps(metadata or {}),
            "created_at": now,
            "updated_at": now,
        }
        sql, params = self._qb.insert("sessions", values)
        await self._db.execute(sql, params)
        return await self.get_by_id(sid)  # type: ignore[return-value]

    async def get_by_id(self, session_id: str) -> dict[str, Any] | None:
        """Get a single session by id."""
        sql, params = self._qb.select("sessions", where={"id": session_id})
        return await self._db.fetch_one(sql, params)

    async def list_by_user(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List sessions for the current user, optionally filtered by status."""
        where: dict[str, Any] = {}
        if status:
            where["status"] = status
        sql, params = self._qb.select(
            "sessions", where=where, order_by="created_at DESC", limit=limit
        )
        return await self._db.fetch_all(sql, params)

    async def update_status(self, session_id: str, status: str) -> None:
        """Update a session's status."""
        now = datetime.now(timezone.utc).isoformat()
        sql, params = self._qb.update(
            "sessions",
            set_={"status": status, "updated_at": now},
            where={"id": session_id},
        )
        await self._db.execute(sql, params)

    async def delete(self, session_id: str) -> None:
        """Delete a session."""
        sql, params = self._qb.delete("sessions", where={"id": session_id})
        await self._db.execute(sql, params)
