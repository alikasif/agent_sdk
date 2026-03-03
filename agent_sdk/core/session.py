"""Session — encapsulates a single conversation for one user."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from agent_sdk.core.message import Message
from agent_sdk.db.connection import DatabaseConnection
from agent_sdk.db.repositories.session_repo import SessionRepository
from agent_sdk.db.repositories.step_repo import StepRepository
from agent_sdk.types import SessionStatus


class Session:
    """Represents a single user conversation with its own state and history."""

    def __init__(
        self,
        *,
        id: str,
        user_id: str,
        agent_name: str,
        status: SessionStatus = SessionStatus.ACTIVE,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        db: DatabaseConnection | None = None,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.agent_name = agent_name
        self.status = status
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self._db = db
        self._session_repo: SessionRepository | None = None
        self._step_repo: StepRepository | None = None
        self._history_mgr: Any | None = None  # Lazy HistoryManager

    def _get_session_repo(self) -> SessionRepository:
        if self._session_repo is None:
            assert self._db is not None, "Session requires a DatabaseConnection for persistence operations."
            self._session_repo = SessionRepository(self._db)
        return self._session_repo

    def _get_step_repo(self) -> StepRepository:
        if self._step_repo is None:
            assert self._db is not None, "Session requires a DatabaseConnection for persistence operations."
            self._step_repo = StepRepository(self._db)
        return self._step_repo

    def _get_history_mgr(self) -> Any:
        if self._history_mgr is None:
            assert self._db is not None, "Session requires a DatabaseConnection for persistence operations."
            from agent_sdk.persistence.history import HistoryManager
            self._history_mgr = HistoryManager(self._db)
        return self._history_mgr

    async def add_message(self, message: Message) -> None:
        """Persist a message to the session's conversation history."""
        mgr = self._get_history_mgr()
        await mgr.append(self.id, message)

    async def get_history(
        self, limit: int = 50, before: datetime | None = None
    ) -> list[Message]:
        """Retrieve conversation history for this session."""
        mgr = self._get_history_mgr()
        return await mgr.get(self.id, limit=limit, before=before)

    async def get_steps(self) -> list[dict[str, Any]]:
        """Get all steps for this session."""
        repo = self._get_step_repo()
        return await repo.get_by_session(self.id)

    async def pause(self) -> None:
        """Pause this session."""
        self.status = SessionStatus.PAUSED
        repo = self._get_session_repo()
        await repo.update_status(self.id, SessionStatus.PAUSED.value)

    async def resume(self) -> None:
        """Resume this session."""
        self.status = SessionStatus.ACTIVE
        repo = self._get_session_repo()
        await repo.update_status(self.id, SessionStatus.ACTIVE.value)

    async def archive(self) -> None:
        """Archive this session."""
        self.status = SessionStatus.ARCHIVED
        repo = self._get_session_repo()
        await repo.update_status(self.id, SessionStatus.ARCHIVED.value)

    @classmethod
    def from_row(cls, row: dict[str, Any], db: DatabaseConnection | None = None) -> Session:
        """Construct a Session from a database row dict."""
        metadata = row.get("metadata", "{}")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            agent_name=row["agent_name"],
            status=SessionStatus(row.get("status", "active")),
            metadata=metadata,
            db=db,
        )

