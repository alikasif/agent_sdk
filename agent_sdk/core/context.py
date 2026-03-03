"""RunContext — request-scoped dependency bag threaded through every call."""

from __future__ import annotations

from typing import Any, TypeVar, TYPE_CHECKING

from agent_sdk.config import Settings
from agent_sdk.db.connection import DatabaseConnection

if TYPE_CHECKING:
    from agent_sdk.core.session import Session


T = TypeVar("T")


class RunContext:
    """Request-scoped context available to every layer during an agent run.

    Holds the user_id, session, agent reference, DB connection, and settings.
    Provides a helper to obtain scoped repository instances.
    """

    def __init__(
        self,
        user_id: str,
        session: Session,
        agent: Any,  # Agent — avoid circular import
        db: DatabaseConnection,
        settings: Settings,
    ) -> None:
        self.user_id = user_id
        self.session = session
        self.agent = agent
        self.db = db
        self.settings = settings

    def get_scoped_repo(self, repo_class: type[T]) -> T:
        """Return a repository instance that is automatically scoped to user_id.

        The user scope is already set via ContextVar when the run starts,
        so every repository operation automatically filters by user_id.
        """
        return repo_class(self.db)  # type: ignore[call-arg]
