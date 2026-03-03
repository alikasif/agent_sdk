"""Policy definitions for governance."""

from __future__ import annotations

from pydantic import BaseModel

from agent_sdk.types import ExecutionPolicy


class PolicyRule(BaseModel):
    """A rule mapping a tool (or wildcard) to an execution policy."""

    tool_name: str | None = None  # None = wildcard (all tools)
    policy: ExecutionPolicy = ExecutionPolicy.AUTO
    condition: str | None = None  # optional expression for advanced matching
    description: str = ""
