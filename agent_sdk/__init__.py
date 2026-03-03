"""agent_sdk — Production-grade SDK for agentic software."""

from agent_sdk._version import __version__
from agent_sdk.config import Settings
from agent_sdk.types import (
    StepStatus,
    SessionStatus,
    RunStatus,
    MessageRole,
    ExecutionPolicy,
    ApprovalStatus,
    MemoryType,
    CircuitState,
)
from agent_sdk.exceptions import (
    AgentSDKError,
    ConfigurationError,
    SessionNotFoundError,
    SessionPausedError,
    StepExecutionError,
    ToolNotFoundError,
    ToolExecutionError,
    IsolationViolationError,
    ApprovalRequiredError,
    ApprovalTimeoutError,
    ApprovalDeniedError,
    CheckpointError,
    ReplayError,
    RateLimitError,
    CircuitOpenError,
    BackpressureError,
    LLMError,
    DiscoveryError,
)

# Core
from agent_sdk.core.agent import Agent, AgentResult
from agent_sdk.core.context import RunContext
from agent_sdk.core.message import Message, ToolCall, ToolResult, StreamEvent, TokenUsage
from agent_sdk.core.session import Session
from agent_sdk.core.step import Step
from agent_sdk.core.tool import Tool, tool

# Governance
from agent_sdk.governance.policy import PolicyRule

# Composability (lazy — requires optional deps)


def create_agent_app(*args, **kwargs):  # type: ignore[no-untyped-def]
    """Lazy wrapper for FastAPI app factory."""
    from agent_sdk.composability.server import create_agent_app as _factory
    return _factory(*args, **kwargs)


__all__ = [
    "__version__",
    "Settings",
    # Core
    "Agent",
    "AgentResult",
    "RunContext",
    "Session",
    "Step",
    "Message",
    "ToolCall",
    "ToolResult",
    "StreamEvent",
    "TokenUsage",
    "Tool",
    "tool",
    # Governance
    "PolicyRule",
    # Composability
    "create_agent_app",
    # Types
    "StepStatus",
    "SessionStatus",
    "RunStatus",
    "MessageRole",
    "ExecutionPolicy",
    "ApprovalStatus",
    "MemoryType",
    "CircuitState",
    # Exceptions
    "AgentSDKError",
    "ConfigurationError",
    "SessionNotFoundError",
    "SessionPausedError",
    "StepExecutionError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "IsolationViolationError",
    "ApprovalRequiredError",
    "ApprovalTimeoutError",
    "ApprovalDeniedError",
    "CheckpointError",
    "ReplayError",
    "RateLimitError",
    "CircuitOpenError",
    "BackpressureError",
    "LLMError",
    "DiscoveryError",
]

