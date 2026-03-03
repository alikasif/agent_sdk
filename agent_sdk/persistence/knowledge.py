"""Knowledge store — key-value + text-chunk knowledge for agent reference."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, Field

from agent_sdk.db.repositories.knowledge_repo import KnowledgeRepository

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection


class KnowledgeEntry(BaseModel):
    """A single knowledge entry."""

    user_id: str = ""
    namespace: str = ""
    key: str = ""
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeStore:
    """High-level knowledge store operations."""

    def __init__(self, knowledge_repo: KnowledgeRepository) -> None:
        self._repo = knowledge_repo

    async def put(
        self,
        user_id: str,
        namespace: str,
        key: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Insert or update a knowledge entry."""
        await self._repo.put(
            namespace=namespace,
            key=key,
            content=content,
            metadata=metadata,
        )

    async def get(
        self, user_id: str, namespace: str, key: str
    ) -> KnowledgeEntry | None:
        """Get a single knowledge entry."""
        row = await self._repo.get(namespace=namespace, key=key)
        if not row:
            return None
        return _row_to_entry(row)

    async def search(
        self,
        user_id: str,
        namespace: str,
        query: str,
        limit: int = 10,
    ) -> list[KnowledgeEntry]:
        """Search knowledge by text match."""
        rows = await self._repo.search(namespace=namespace, query=query, limit=limit)
        return [_row_to_entry(r) for r in rows]

    async def delete(self, user_id: str, namespace: str, key: str) -> None:
        """Delete a knowledge entry."""
        await self._repo.delete(namespace=namespace, key=key)

    async def list_namespaces(self, user_id: str) -> list[str]:
        """List all namespaces for a user."""
        return await self._repo.list_namespaces()


def _row_to_entry(row: dict[str, Any]) -> KnowledgeEntry:
    """Convert a DB row to a KnowledgeEntry."""
    metadata = row.get("metadata", "{}")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = {}
    return KnowledgeEntry(
        user_id=row.get("user_id", ""),
        namespace=row.get("namespace", ""),
        key=row.get("key", ""),
        content=row.get("content", ""),
        metadata=metadata,
        created_at=row.get("created_at", datetime.now(timezone.utc)),
        updated_at=row.get("updated_at", datetime.now(timezone.utc)),
    )
