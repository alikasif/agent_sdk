"""Repository for steps table access."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from agent_sdk.isolation.filter import ScopedQueryBuilder

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection


class StepRepository:
    """CRUD operations for the steps table, scoped by user_id."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self._qb = ScopedQueryBuilder()

    async def create(
        self,
        session_id: str,
        step_number: int,
        idempotency_key: str | None = None,
        input_messages: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new step record."""
        step_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        idem_key = idempotency_key or uuid4().hex
        values: dict[str, Any] = {
            "id": step_id,
            "session_id": session_id,
            "step_number": step_number,
            "status": "pending",
            "input_messages": json.dumps(input_messages or []),
            "output_message": None,
            "tool_calls": json.dumps([]),
            "tool_results": json.dumps([]),
            "checkpoint": None,
            "idempotency_key": idem_key,
            "error": None,
            "started_at": now,
            "completed_at": None,
        }
        sql, params = self._qb.insert("steps", values)
        await self._db.execute(sql, params)
        return await self.get_by_id(step_id)  # type: ignore[return-value]

    async def get_by_id(self, step_id: str) -> dict[str, Any] | None:
        """Get a single step by id."""
        sql, params = self._qb.select("steps", where={"id": step_id})
        return await self._db.fetch_one(sql, params)

    async def get_by_session(self, session_id: str) -> list[dict[str, Any]]:
        """Get all steps for a session, ordered by step_number."""
        sql, params = self._qb.select(
            "steps", where={"session_id": session_id}, order_by="step_number ASC"
        )
        return await self._db.fetch_all(sql, params)

    async def get_latest_by_session(self, session_id: str) -> dict[str, Any] | None:
        """Get the most recent step for a session."""
        sql, params = self._qb.select(
            "steps",
            where={"session_id": session_id},
            order_by="step_number DESC",
            limit=1,
        )
        return await self._db.fetch_one(sql, params)

    async def update_status(
        self,
        step_id: str,
        status: str,
        *,
        output_message: dict[str, Any] | None = None,
        tool_calls: list[Any] | None = None,
        tool_results: list[Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Update a step's status and optional fields."""
        set_: dict[str, Any] = {"status": status}
        now = datetime.now(timezone.utc).isoformat()
        if status == "completed":
            set_["completed_at"] = now
        if status == "running":
            set_["started_at"] = now
        if output_message is not None:
            set_["output_message"] = json.dumps(output_message)
        if tool_calls is not None:
            set_["tool_calls"] = json.dumps(tool_calls)
        if tool_results is not None:
            set_["tool_results"] = json.dumps(tool_results)
        if error is not None:
            set_["error"] = error

        sql, params = self._qb.update("steps", set_=set_, where={"id": step_id})
        await self._db.execute(sql, params)

    async def save_checkpoint(self, step_id: str, checkpoint: bytes) -> None:
        """Save a serialized checkpoint blob for a step."""
        sql, params = self._qb.update(
            "steps", set_={"checkpoint": checkpoint}, where={"id": step_id}
        )
        await self._db.execute(sql, params)

    async def list_checkpoints(self, session_id: str) -> list[dict[str, Any]]:
        """List step summaries that have checkpoints for a session."""
        sql, params = self._qb.select(
            "steps",
            columns="id, session_id, step_number, status, idempotency_key, started_at, completed_at",
            where={"session_id": session_id},
            order_by="step_number ASC",
        )
        rows = await self._db.fetch_all(sql, params)
        return [r for r in rows if r.get("status") == "completed"]
