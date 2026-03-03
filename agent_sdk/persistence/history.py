"""Conversation history — append, retrieve, paginate."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from agent_sdk.core.message import Message, ToolCall
from agent_sdk.isolation.scope import get_user_scope

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection


class HistoryManager:
    """Append-only conversation history with retrieval and pagination."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    async def append(self, session_id: str, message: Message) -> None:
        """Append a message to the session history."""
        user_id = get_user_scope()
        count_row = await self._db.fetch_one(
            "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
            [session_id],
        )
        ordinal = (count_row["cnt"] if count_row else 0) + 1
        msg_id = uuid4().hex
        sql = (
            "INSERT INTO messages (id, session_id, user_id, role, content, "
            "tool_calls, tool_call_id, name, metadata, timestamp, ordinal) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = [
            msg_id,
            session_id,
            user_id,
            message.role.value if hasattr(message.role, "value") else message.role,
            message.content,
            json.dumps([tc.model_dump() for tc in message.tool_calls]) if message.tool_calls else None,
            message.tool_call_id,
            message.name,
            json.dumps(message.metadata) if message.metadata else "{}",
            message.timestamp.isoformat() if message.timestamp else datetime.now(timezone.utc).isoformat(),
            ordinal,
        ]
        await self._db.execute(sql, params)

    async def get(
        self,
        session_id: str,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[Message]:
        """Get messages for a session, optionally before a timestamp."""
        if before:
            sql = (
                "SELECT * FROM messages WHERE session_id = ? AND timestamp < ? "
                "ORDER BY ordinal ASC LIMIT ?"
            )
            params: list[Any] = [session_id, before.isoformat(), limit]
        else:
            sql = (
                "SELECT * FROM messages WHERE session_id = ? "
                "ORDER BY ordinal ASC LIMIT ?"
            )
            params = [session_id, limit]
        rows = await self._db.fetch_all(sql, params)
        return [_row_to_message(r) for r in rows]

    async def get_full(self, session_id: str) -> list[Message]:
        """Get the complete history for a session."""
        sql = "SELECT * FROM messages WHERE session_id = ? ORDER BY ordinal ASC"
        rows = await self._db.fetch_all(sql, [session_id])
        return [_row_to_message(r) for r in rows]

    async def count(self, session_id: str) -> int:
        """Count messages in a session."""
        row = await self._db.fetch_one(
            "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
            [session_id],
        )
        return row["cnt"] if row else 0

    async def truncate(self, session_id: str, keep_last: int) -> None:
        """Delete older messages, keeping only the last N."""
        sql = (
            "DELETE FROM messages WHERE session_id = ? AND id NOT IN "
            "(SELECT id FROM messages WHERE session_id = ? ORDER BY ordinal DESC LIMIT ?)"
        )
        await self._db.execute(sql, [session_id, session_id, keep_last])


def _row_to_message(row: dict[str, Any]) -> Message:
    """Convert a DB row to a Message."""
    tool_calls = None
    tc_raw = row.get("tool_calls")
    if tc_raw and isinstance(tc_raw, str):
        try:
            tc_data = json.loads(tc_raw)
            if tc_data:
                tool_calls = [ToolCall.model_validate(tc) for tc in tc_data]
        except (json.JSONDecodeError, TypeError):
            pass
    metadata = row.get("metadata", "{}")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = {}
    return Message(
        role=row["role"],
        content=row.get("content"),
        tool_calls=tool_calls,
        tool_call_id=row.get("tool_call_id"),
        name=row.get("name"),
        metadata=metadata,
    )
