"""Failure detection and automatic resume orchestration."""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection

logger = logging.getLogger("agent_sdk.durability.recovery")


class RecoveryManager:
    """Detects incomplete runs and orchestrates automatic resume."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    async def detect_incomplete(self) -> list[str]:
        """Return session_ids with uncompleted runs (running steps) for the current user."""
        from agent_sdk.isolation.scope import get_user_scope
        user_id = get_user_scope()
        rows = await self._db.fetch_all(
            "SELECT DISTINCT session_id FROM steps WHERE status IN ('pending', 'running') AND user_id = ?",
            [user_id],
        )
        return [r["session_id"] for r in rows]

    async def auto_resume(self, session_id: str, agent: Any) -> Any:
        """Automatically resume an incomplete session.

        Parameters
        ----------
        session_id:
            The session to resume.
        agent:
            An Agent instance to call run(resume=True).

        Returns
        -------
        AgentResult from the resumed run.
        """
        # Look up user_id for this session
        row = await self._db.fetch_one(
            "SELECT user_id FROM sessions WHERE id = ?", [session_id]
        )
        if not row:
            logger.error("Session %s not found for auto-resume.", session_id)
            return None

        user_id = row["user_id"]
        logger.info("Auto-resuming session %s for user %s", session_id, user_id)
        return await agent.run(
            user_id=user_id,
            input=None,
            session_id=session_id,
            resume=True,
        )
