"""Exception hierarchy for the Agent SDK.

All SDK exceptions inherit from AgentSDKError, making it easy to
catch any SDK-originated error with a single except clause.
"""

from __future__ import annotations


class AgentSDKError(Exception):
    """Base exception for all SDK errors."""


class ConfigurationError(AgentSDKError):
    """Invalid or missing configuration."""


class SessionNotFoundError(AgentSDKError):
    """Requested session does not exist."""


class SessionPausedError(AgentSDKError):
    """Session is paused and requires action (approval or explicit resume)."""


class StepExecutionError(AgentSDKError):
    """A step failed during execution."""


class ToolNotFoundError(AgentSDKError):
    """Referenced tool is not registered."""


class ToolExecutionError(AgentSDKError):
    """Tool execution failed."""


class IsolationViolationError(AgentSDKError):
    """A cross-user data access was detected."""


class ApprovalRequiredError(AgentSDKError):
    """Tool execution requires approval before proceeding."""


class ApprovalTimeoutError(AgentSDKError):
    """Approval was not resolved within the timeout period."""


class ApprovalDeniedError(AgentSDKError):
    """Approval request was denied."""


class CheckpointError(AgentSDKError):
    """Failed to save or load a checkpoint."""


class ReplayError(AgentSDKError):
    """Failed to replay steps from checkpoints."""


class RateLimitError(AgentSDKError):
    """Rate limit exceeded."""


class CircuitOpenError(AgentSDKError):
    """Circuit breaker is open; call rejected."""


class BackpressureError(AgentSDKError):
    """Request queue is full; apply backpressure."""


class LLMError(AgentSDKError):
    """LLM provider returned an error."""


class DiscoveryError(AgentSDKError):
    """Agent discovery failed."""
