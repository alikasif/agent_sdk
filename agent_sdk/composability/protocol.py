"""Agent-to-agent request/response protocol schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent_sdk.core.message import Message, TokenUsage
from agent_sdk.types import RunStatus


class AgentRequest(BaseModel):
    """Canonical request to an agent service."""

    user_id: str
    input: str | list[Message]
    session_id: str | None = None
    max_steps: int = 30
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Canonical response from an agent service."""

    session_id: str
    user_id: str
    output: str
    messages: list[Message] = Field(default_factory=list)
    status: RunStatus = RunStatus.COMPLETED
    usage: TokenUsage | None = None
