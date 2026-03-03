"""Session CRUD — create, load, list, archive sessions."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from agent_sdk.core.session import Session
from agent_sdk.db.repositories.session_repo import SessionRepository
from agent_sdk.exceptions import SessionNotFoundError
from agent_sdk.types import SessionStatus

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection


class SessionStore:
    """High-level session lifecycle management."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self._repo = SessionRepository(db)

    async def create(
        self,
        user_id: str,
        agent_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """Create a new session."""
        row = await self._repo.create(agent_name=agent_name, metadata=metadata)
        return Session.from_row(row, db=self._db)

    async def load(self, session_id: str) -> Session:
        """Load an existing session by id."""
        row = await self._repo.get_by_id(session_id)
        if not row:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        return Session.from_row(row, db=self._db)

    async def list_sessions(
        self,
        user_id: str,
        status: SessionStatus | None = None,
        limit: int = 20,
    ) -> list[Session]:
        """List sessions for a user."""
        status_val = status.value if status else None
        rows = await self._repo.list_by_user(status=status_val, limit=limit)
        return [Session.from_row(r, db=self._db) for r in rows]

    async def update_status(self, session_id: str, status: SessionStatus) -> None:
        """Update a session's status."""
        await self._repo.update_status(session_id, status.value)

    async def archive(self, session_id: str) -> None:
        """Archive a session."""
        await self._repo.update_status(session_id, SessionStatus.ARCHIVED.value)

    async def delete(self, session_id: str) -> None:
        """Delete a session."""
        await self._repo.delete(session_id)
