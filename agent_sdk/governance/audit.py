"""Audit log — every tool call, decision, and approval is recorded."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

from agent_sdk.db.repositories.audit_repo import AuditRepository

if TYPE_CHECKING:
    from agent_sdk.core.context import RunContext

logger = logging.getLogger("agent_sdk.governance.audit")


class AuditEntry(BaseModel):
    """A single audit log entry."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = ""
    session_id: str | None = None
    action: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class AuditLogger:
    """Writes immutable audit log entries for every significant action."""

    def __init__(self, audit_repo: AuditRepository) -> None:
        self._repo = audit_repo

    async def log(
        self,
        ctx: RunContext,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an action with context."""
        await self._repo.create(
            action=action,
            details=details,
            session_id=ctx.session.id,
        )
        logger.debug("Audit: %s user=%s session=%s", action, ctx.user_id, ctx.session.id)

    async def query(
        self,
        user_id: str | None = None,
        action: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit log entries."""
        import json
        since_str = since.isoformat() if since else None
        rows = await self._repo.query(
            user_id=user_id,
            action=action,
            since=since_str,
            limit=limit,
        )
        entries: list[AuditEntry] = []
        for r in rows:
            details = r.get("details", {})
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except (json.JSONDecodeError, TypeError):
                    details = {}
            entries.append(
                AuditEntry(
                    id=r["id"],
                    timestamp=r["timestamp"],
                    user_id=r["user_id"],
                    session_id=r.get("session_id"),
                    action=r["action"],
                    details=details,
                )
            )
        return entries
