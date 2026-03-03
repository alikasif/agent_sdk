"""Repository for memory table access."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from agent_sdk.isolation.filter import ScopedQueryBuilder

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection


class MemoryRepository:
    """CRUD operations for the memory table, scoped by user_id."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self._qb = ScopedQueryBuilder()

    async def create(
        self,
        key: str,
        value: str,
        memory_type: str,
        session_id: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new memory entry."""
        mem_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        values: dict[str, Any] = {
            "id": mem_id,
            "session_id": session_id,
            "key": key,
            "value": value,
            "memory_type": memory_type,
            "tags": json.dumps(tags or []),
            "created_at": now,
        }
        sql, params = self._qb.insert("memory", values)
        await self._db.execute(sql, params)
        return {"id": mem_id, **values}

    async def get_by_user(
        self,
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get memory entries for the current user."""
        where: dict[str, Any] = {}
        if memory_type:
            where["memory_type"] = memory_type
        sql, params = self._qb.select(
            "memory", where=where, order_by="created_at DESC", limit=limit
        )
        return await self._db.fetch_all(sql, params)

    async def get_by_session(
        self,
        session_id: str,
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get memory entries for a specific session."""
        where: dict[str, Any] = {"session_id": session_id}
        if memory_type:
            where["memory_type"] = memory_type
        sql, params = self._qb.select(
            "memory", where=where, order_by="created_at DESC", limit=limit
        )
        return await self._db.fetch_all(sql, params)

    async def search(
        self,
        query: str,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search memory by text match on key or value."""
        from agent_sdk.isolation.scope import get_user_scope

        user_id = get_user_scope()
        conditions = ["user_id = ?", "(key LIKE ? OR value LIKE ?)"]
        params: list[Any] = [user_id, f"%{query}%", f"%{query}%"]
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type)

        sql = f"SELECT * FROM memory WHERE {' AND '.join(conditions)} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return await self._db.fetch_all(sql, params)

    async def delete(self, memory_id: str) -> None:
        """Delete a memory entry."""
        sql, params = self._qb.delete("memory", where={"id": memory_id})
        await self._db.execute(sql, params)
