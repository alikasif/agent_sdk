"""Shared enums and type aliases for the Agent SDK."""

from __future__ import annotations

from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    """Status of a single step in the agent execution loop."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SessionStatus(str, Enum):
    """Status of an agent session."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RunStatus(str, Enum):
    """Outcome of an Agent.run() invocation."""

    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


class MessageRole(str, Enum):
    """Role of a message in the conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ExecutionPolicy(str, Enum):
    """Authority level required to execute a tool."""

    AUTO = "auto"
    HUMAN_APPROVAL = "human_approval"
    ADMIN_SIGNOFF = "admin_signoff"


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class MemoryType(str, Enum):
    """Type of memory entry."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class CircuitState(str, Enum):
    """State of a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# Type aliases
JSON = dict[str, Any]
"""Generic JSON-compatible dictionary."""
