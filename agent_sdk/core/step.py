"""Step model — atomic unit of agent work (one think→act→observe cycle)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from agent_sdk.core.message import Message, ToolCall, ToolResult
from agent_sdk.types import StepStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Step(BaseModel):
    """Atomic unit of agent work: one think→act→observe cycle."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str
    step_number: int
    status: StepStatus = StepStatus.PENDING
    input_messages: list[Message] = Field(default_factory=list)
    output_message: Message | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    checkpoint: bytes | None = None
    idempotency_key: str = Field(default_factory=lambda: uuid4().hex)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    def mark_running(self) -> None:
        """Transition to running state."""
        self.status = StepStatus.RUNNING
        self.started_at = _utcnow()

    def mark_completed(self) -> None:
        """Transition to completed state."""
        self.status = StepStatus.COMPLETED
        self.completed_at = _utcnow()

    def mark_failed(self, error: str) -> None:
        """Transition to failed state with error detail."""
        self.status = StepStatus.FAILED
        self.error = error
        self.completed_at = _utcnow()
