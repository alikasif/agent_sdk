"""Repository for knowledge table access."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from agent_sdk.isolation.scope import get_user_scope

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection


class KnowledgeRepository:
    """CRUD operations for the knowledge table.

    The knowledge table uses a composite primary key (user_id, namespace, key)
    so we use get_user_scope() directly for isolation.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    async def put(
        self,
        namespace: str,
        key: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Insert or replace a knowledge entry."""
        user_id = get_user_scope()
        now = datetime.now(timezone.utc).isoformat()
        sql = """
            INSERT INTO knowledge (user_id, namespace, key, content, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, namespace, key)
            DO UPDATE SET content = excluded.content,
                          metadata = excluded.metadata,
                          updated_at = excluded.updated_at
        """
        params = [user_id, namespace, key, content, json.dumps(metadata or {}), now, now]
        await self._db.execute(sql, params)

    async def get(self, namespace: str, key: str) -> dict[str, Any] | None:
        """Get a single knowledge entry."""
        user_id = get_user_scope()
        sql = "SELECT * FROM knowledge WHERE user_id = ? AND namespace = ? AND key = ?"
        return await self._db.fetch_one(sql, [user_id, namespace, key])

    async def search(
        self,
        namespace: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search knowledge by text match on key or content."""
        user_id = get_user_scope()
        sql = (
            "SELECT * FROM knowledge "
            "WHERE user_id = ? AND namespace = ? AND (key LIKE ? OR content LIKE ?) "
            "ORDER BY updated_at DESC LIMIT ?"
        )
        return await self._db.fetch_all(sql, [user_id, namespace, f"%{query}%", f"%{query}%", limit])

    async def delete(self, namespace: str, key: str) -> None:
        """Delete a single knowledge entry."""
        user_id = get_user_scope()
        sql = "DELETE FROM knowledge WHERE user_id = ? AND namespace = ? AND key = ?"
        await self._db.execute(sql, [user_id, namespace, key])

    async def list_namespaces(self) -> list[str]:
        """List all distinct namespaces for the current user."""
        user_id = get_user_scope()
        sql = "SELECT DISTINCT namespace FROM knowledge WHERE user_id = ? ORDER BY namespace"
        rows = await self._db.fetch_all(sql, [user_id])
        return [r["namespace"] for r in rows]
