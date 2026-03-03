"""Service registry — register and discover agents."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, Field

from agent_sdk.db.repositories.agent_registry_repo import AgentRegistryRepository
from agent_sdk.exceptions import DiscoveryError

if TYPE_CHECKING:
    from agent_sdk.db.connection import DatabaseConnection

logger = logging.getLogger("agent_sdk.composability.discovery")


class AgentDescriptor(BaseModel):
    """Description of a registered agent service."""

    name: str
    description: str = ""
    base_url: str = ""
    tools: list[str] = Field(default_factory=list)
    version: str = "0.1.0"
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    health_url: str = ""


class ServiceRegistry:
    """Registry for agents to register and discover each other."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._repo = AgentRegistryRepository(db)

    async def register(self, descriptor: AgentDescriptor) -> None:
        """Register an agent in the registry."""
        await self._repo.register(
            name=descriptor.name,
            description=descriptor.description,
            base_url=descriptor.base_url,
            tools=descriptor.tools,
            version=descriptor.version,
            health_url=descriptor.health_url,
        )
        logger.info("Registered agent: %s at %s", descriptor.name, descriptor.base_url)

    async def deregister(self, name: str) -> None:
        """Remove an agent from the registry."""
        await self._repo.deregister(name)
        logger.info("Deregistered agent: %s", name)

    async def discover(self, name: str) -> AgentDescriptor | None:
        """Look up an agent by name."""
        row = await self._repo.get_by_name(name)
        if not row:
            return None
        return _row_to_descriptor(row)

    async def list_agents(self) -> list[AgentDescriptor]:
        """List all registered agents."""
        rows = await self._repo.list_all()
        return [_row_to_descriptor(r) for r in rows]

    async def health_check_all(self) -> dict[str, bool]:
        """Check health of all registered agents."""
        results: dict[str, bool] = {}
        agents = await self.list_agents()
        for agent in agents:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(agent.health_url)
                    results[agent.name] = resp.status_code == 200
                    if resp.status_code == 200:
                        await self._repo.update_last_seen(agent.name)
            except Exception:
                results[agent.name] = False
        return results


def _row_to_descriptor(row: dict[str, Any]) -> AgentDescriptor:
    """Convert a DB row to an AgentDescriptor."""
    import json
    tools = row.get("tools", "[]")
    if isinstance(tools, str):
        try:
            tools = json.loads(tools)
        except (json.JSONDecodeError, TypeError):
            tools = []
    return AgentDescriptor(
        name=row["name"],
        description=row.get("description", ""),
        base_url=row.get("base_url", ""),
        tools=tools,
        version=row.get("version", "0.1.0"),
        health_url=row.get("health_url", ""),
    )
