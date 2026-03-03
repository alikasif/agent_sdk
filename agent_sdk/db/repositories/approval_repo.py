"""Repository for approvals table access."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from agent_sdk.isolation.filter import ScopedQueryBuilder

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection


class ApprovalRepository:
    """CRUD operations for the approvals table, scoped by user_id."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self._qb = ScopedQueryBuilder()

    async def create(
        self,
        session_id: str,
        step_number: int,
        tool_name: str,
        tool_arguments: dict[str, Any],
        required_policy: str,
    ) -> dict[str, Any]:
        """Create a new pending approval request."""
        approval_id = uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        values: dict[str, Any] = {
            "id": approval_id,
            "session_id": session_id,
            "step_number": step_number,
            "tool_name": tool_name,
            "tool_arguments": json.dumps(tool_arguments),
            "required_policy": required_policy,
            "status": "pending",
            "requested_at": now,
            "resolved_at": None,
            "resolved_by": None,
            "reason": None,
        }
        sql, params = self._qb.insert("approvals", values)
        await self._db.execute(sql, params)
        return await self.get_by_id(approval_id)  # type: ignore[return-value]

    async def get_by_id(self, approval_id: str) -> dict[str, Any] | None:
        """Get a single approval by id."""
        sql, params = self._qb.select("approvals", where={"id": approval_id})
        return await self._db.fetch_one(sql, params)

    async def get_pending(self) -> list[dict[str, Any]]:
        """Get all pending approvals for the current user."""
        sql, params = self._qb.select(
            "approvals", where={"status": "pending"}, order_by="requested_at ASC"
        )
        return await self._db.fetch_all(sql, params)

    async def resolve(
        self,
        approval_id: str,
        status: str,
        resolved_by: str,
        reason: str = "",
    ) -> None:
        """Resolve an approval (approved/denied/expired)."""
        now = datetime.now(timezone.utc).isoformat()
        sql, params = self._qb.update(
            "approvals",
            set_={
                "status": status,
                "resolved_at": now,
                "resolved_by": resolved_by,
                "reason": reason,
            },
            where={"id": approval_id},
        )
        await self._db.execute(sql, params)

    async def get_by_session(self, session_id: str) -> list[dict[str, Any]]:
        """Get all approvals for a session."""
        sql, params = self._qb.select(
            "approvals", where={"session_id": session_id}, order_by="requested_at ASC"
        )
        return await self._db.fetch_all(sql, params)
