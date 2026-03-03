"""Repository for agent_registry table access."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection


class AgentRegistryRepository:
    """CRUD operations for the agent_registry table.

    The agent_registry is NOT scoped by user_id — it is a global
    service directory shared across the entire SDK instance.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    async def register(
        self,
        name: str,
        description: str,
        base_url: str,
        tools: list[str] | None = None,
        version: str = "0.1.0",
        health_url: str | None = None,
    ) -> dict[str, Any]:
        """Register or update an agent in the registry."""
        now = datetime.now(timezone.utc).isoformat()
        h_url = health_url or f"{base_url.rstrip('/')}/health"
        sql = """
            INSERT INTO agent_registry (name, description, base_url, tools, version, health_url, registered_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name)
            DO UPDATE SET description = excluded.description,
                          base_url = excluded.base_url,
                          tools = excluded.tools,
                          version = excluded.version,
                          health_url = excluded.health_url,
                          last_seen_at = excluded.last_seen_at
        """
        params = [name, description, base_url, json.dumps(tools or []), version, h_url, now, now]
        await self._db.execute(sql, params)
        return await self.get_by_name(name)  # type: ignore[return-value]

    async def deregister(self, name: str) -> None:
        """Remove an agent from the registry."""
        await self._db.execute("DELETE FROM agent_registry WHERE name = ?", [name])

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Look up an agent by name."""
        return await self._db.fetch_one(
            "SELECT * FROM agent_registry WHERE name = ?", [name]
        )

    async def list_all(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        return await self._db.fetch_all(
            "SELECT * FROM agent_registry ORDER BY name"
        )

    async def update_last_seen(self, name: str) -> None:
        """Bump the last_seen_at timestamp for an agent."""
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE agent_registry SET last_seen_at = ? WHERE name = ?",
            [now, name],
        )
