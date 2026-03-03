"""Message and related Pydantic models for the Agent SDK."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from agent_sdk.types import MessageRole


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ToolCall(BaseModel):
    """A single tool invocation requested by the LLM."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result of executing a tool."""

    tool_call_id: str
    output: Any = None
    error: str | None = None
    idempotency_key: str = Field(default_factory=lambda: uuid4().hex)


class TokenUsage(BaseModel):
    """Token usage reported by the LLM provider."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Message(BaseModel):
    """A single message in the conversation."""

    role: MessageRole
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None
    timestamp: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Parsed response from an LLM provider."""

    message: Message
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: TokenUsage = Field(default_factory=TokenUsage)


class StreamEvent(BaseModel):
    """A single event in a streaming response."""

    event: str  # step_start, token, tool_call, tool_result, step_end, done, error
    data: dict[str, Any] = Field(default_factory=dict)
