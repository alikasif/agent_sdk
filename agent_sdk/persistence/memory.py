"""Memory manager — short-term (buffer) + long-term (summary)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

from agent_sdk.db.repositories.memory_repo import MemoryRepository
from agent_sdk.types import MemoryType

if TYPE_CHECKING:
    from agent_sdk.core.context import RunContext

logger = logging.getLogger("agent_sdk.persistence.memory")


class MemoryEntry(BaseModel):
    """A single memory entry."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    user_id: str = ""
    session_id: str | None = None
    key: str = ""
    value: str = ""
    memory_type: MemoryType = MemoryType.SHORT_TERM
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryManager:
    """Two-tier memory: short-term buffer + long-term summaries."""

    def __init__(self, memory_repo: MemoryRepository) -> None:
        self._repo = memory_repo

    async def add_short_term(self, ctx: RunContext, key: str, value: str) -> None:
        """Add a short-term memory entry for the current session."""
        await self._repo.create(
            key=key,
            value=value,
            memory_type=MemoryType.SHORT_TERM.value,
            session_id=ctx.session.id,
        )

    async def get_short_term(self, ctx: RunContext, limit: int = 10) -> list[MemoryEntry]:
        """Get short-term memory entries for the current session."""
        rows = await self._repo.get_by_session(
            session_id=ctx.session.id,
            memory_type=MemoryType.SHORT_TERM.value,
            limit=limit,
        )
        return [_row_to_entry(r) for r in rows]

    async def add_long_term(
        self,
        ctx: RunContext,
        key: str,
        value: str,
        tags: list[str] | None = None,
    ) -> None:
        """Add a long-term memory entry (cross-session)."""
        await self._repo.create(
            key=key,
            value=value,
            memory_type=MemoryType.LONG_TERM.value,
            session_id=None,  # cross-session
            tags=tags,
        )

    async def search_long_term(
        self, ctx: RunContext, query: str, limit: int = 5
    ) -> list[MemoryEntry]:
        """Search long-term memory entries."""
        rows = await self._repo.search(
            query=query,
            memory_type=MemoryType.LONG_TERM.value,
            limit=limit,
        )
        return [_row_to_entry(r) for r in rows]

    async def summarize_and_promote(self, ctx: RunContext) -> None:
        """Summarize short-term buffer into long-term storage.

        This is a simplified implementation that concatenates short-term
        entries and stores them as a long-term summary.
        """
        short_term = await self.get_short_term(ctx, limit=100)
        if not short_term:
            return

        summary_parts = [f"{e.key}: {e.value}" for e in short_term]
        summary = "; ".join(summary_parts)

        await self.add_long_term(
            ctx,
            key=f"summary_{ctx.session.id}",
            value=summary,
            tags=["auto_summary"],
        )

        # Clear short-term entries
        for entry in short_term:
            await self._repo.delete(entry.id)

        logger.info("Promoted %d short-term entries to long-term for session %s", len(short_term), ctx.session.id)

    async def clear(self, ctx: RunContext) -> None:
        """Clear all memory for the current session."""
        rows = await self._repo.get_by_session(session_id=ctx.session.id)
        for row in rows:
            await self._repo.delete(row["id"])


def _row_to_entry(row: dict[str, Any]) -> MemoryEntry:
    """Convert a DB row to a MemoryEntry."""
    import json
    tags = row.get("tags", "[]")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []
    return MemoryEntry(
        id=row.get("id", ""),
        user_id=row.get("user_id", ""),
        session_id=row.get("session_id"),
        key=row.get("key", ""),
        value=row.get("value", ""),
        memory_type=MemoryType(row.get("memory_type", "short_term")),
        tags=tags,
    )
