"""Approval workflow engine — request, wait, resolve."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

from agent_sdk.db.repositories.approval_repo import ApprovalRepository
from agent_sdk.exceptions import (
    ApprovalDeniedError,
    ApprovalRequiredError,
    ApprovalTimeoutError,
)
from agent_sdk.types import ApprovalStatus, ExecutionPolicy

if TYPE_CHECKING:
    from agent_sdk.core.context import RunContext
    from agent_sdk.core.message import ToolCall

logger = logging.getLogger("agent_sdk.governance.approval")


class ApprovalRequest(BaseModel):
    """An approval request record."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str = ""
    user_id: str = ""
    step_number: int = 0
    tool_call: dict[str, Any] = Field(default_factory=dict)
    required_policy: ExecutionPolicy = ExecutionPolicy.HUMAN_APPROVAL
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    reason: str | None = None


class ApprovalManager:
    """Manages approval request lifecycle."""

    def __init__(self, approval_repo: ApprovalRepository) -> None:
        self._repo = approval_repo

    async def request_approval(
        self,
        ctx: RunContext,
        tool_call: ToolCall,
        policy: ExecutionPolicy,
        step_number: int = 0,
    ) -> ApprovalRequest:
        """Create a pending approval request in the DB."""
        row = await self._repo.create(
            session_id=ctx.session.id,
            step_number=step_number,
            tool_name=tool_call.tool_name,
            tool_arguments=tool_call.arguments,
            required_policy=policy.value,
        )
        logger.info(
            "Approval requested: tool=%s session=%s policy=%s",
            tool_call.tool_name,
            ctx.session.id,
            policy.value,
        )
        return ApprovalRequest(
            id=row["id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            step_number=row["step_number"],
            tool_call=tool_call.model_dump() if hasattr(tool_call, "model_dump") else dict(tool_call),
            required_policy=ExecutionPolicy(row["required_policy"]),
            status=ApprovalStatus(row["status"]),
        )

    async def resolve(
        self,
        request_id: str,
        decision: ApprovalStatus,
        resolved_by: str,
        reason: str = "",
    ) -> ApprovalRequest:
        """Resolve an approval (approved/denied/expired)."""
        await self._repo.resolve(
            approval_id=request_id,
            status=decision.value,
            resolved_by=resolved_by,
            reason=reason,
        )
        row = await self._repo.get_by_id(request_id)
        if not row:
            return ApprovalRequest(id=request_id, status=decision)
        return ApprovalRequest(
            id=row["id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            step_number=row["step_number"],
            status=ApprovalStatus(row["status"]),
            resolved_by=row.get("resolved_by"),
            reason=row.get("reason"),
        )

    async def get_pending(self, user_id: str | None = None) -> list[ApprovalRequest]:
        """Get all pending approvals for the current user."""
        rows = await self._repo.get_pending()
        return [
            ApprovalRequest(
                id=r["id"],
                session_id=r["session_id"],
                user_id=r["user_id"],
                step_number=r["step_number"],
                status=ApprovalStatus(r["status"]),
            )
            for r in rows
        ]

    async def wait_for_resolution(
        self,
        request_id: str,
        timeout: float = 300.0,
    ) -> ApprovalRequest:
        """Poll DB until the approval is resolved or timeout expires."""
        elapsed = 0.0
        poll_interval = 1.0
        while elapsed < timeout:
            row = await self._repo.get_by_id(request_id)
            if row and row["status"] != ApprovalStatus.PENDING.value:
                status = ApprovalStatus(row["status"])
                if status == ApprovalStatus.DENIED:
                    raise ApprovalDeniedError(f"Approval {request_id} was denied.")
                return ApprovalRequest(
                    id=row["id"],
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    step_number=row["step_number"],
                    status=status,
                    resolved_by=row.get("resolved_by"),
                    reason=row.get("reason"),
                )
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        raise ApprovalTimeoutError(f"Approval {request_id} timed out after {timeout}s.")
