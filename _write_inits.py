"""Temporary script to write all __init__.py files."""
import pathlib

base = pathlib.Path(r"d:\GitHub\agent_sdk\agent_sdk")

# core/__init__.py
(base / "core" / "__init__.py").write_text(
    '"""Core runtime \u2014 Agent, Session, Step, Context, tools, LLM, messages."""\n'
    "\n"
    "from agent_sdk.core.agent import Agent, AgentResult\n"
    "from agent_sdk.core.context import RunContext\n"
    "from agent_sdk.core.llm import LLMAdapter, LiteLLMAdapter\n"
    "from agent_sdk.core.message import (\n"
    "    LLMResponse,\n"
    "    Message,\n"
    "    StreamEvent,\n"
    "    TokenUsage,\n"
    "    ToolCall,\n"
    "    ToolResult,\n"
    ")\n"
    "from agent_sdk.core.session import Session\n"
    "from agent_sdk.core.step import Step\n"
    "from agent_sdk.core.tool import Tool, ToolRegistry, tool\n"
    "\n"
    "__all__ = [\n"
    '    "Agent",\n'
    '    "AgentResult",\n'
    '    "LLMAdapter",\n'
    '    "LLMResponse",\n'
    '    "LiteLLMAdapter",\n'
    '    "Message",\n'
    '    "RunContext",\n'
    '    "Session",\n'
    '    "Step",\n'
    '    "StreamEvent",\n'
    '    "TokenUsage",\n'
    '    "Tool",\n'
    '    "ToolCall",\n'
    '    "ToolRegistry",\n'
    '    "ToolResult",\n'
    '    "tool",\n'
    "]\n",
    encoding="utf-8",
)

# db/__init__.py
(base / "db" / "__init__.py").write_text(
    '"""Database layer \u2014 connection pool, migrations, models, repositories."""\n'
    "\n"
    "from agent_sdk.db.connection import DatabaseConnection\n"
    "from agent_sdk.db.migrations import MigrationRunner\n"
    "from agent_sdk.db.models import row_to_dict, row_to_model, model_to_row\n"
    "from agent_sdk.db.repositories import (\n"
    "    AgentRegistryRepository,\n"
    "    ApprovalRepository,\n"
    "    AuditRepository,\n"
    "    KnowledgeRepository,\n"
    "    MemoryRepository,\n"
    "    SessionRepository,\n"
    "    StepRepository,\n"
    ")\n"
    "\n"
    "__all__ = [\n"
    '    "DatabaseConnection",\n'
    '    "MigrationRunner",\n'
    '    "row_to_dict",\n'
    '    "row_to_model",\n'
    '    "model_to_row",\n'
    '    "AgentRegistryRepository",\n'
    '    "ApprovalRepository",\n'
    '    "AuditRepository",\n'
    '    "KnowledgeRepository",\n'
    '    "MemoryRepository",\n'
    '    "SessionRepository",\n'
    '    "StepRepository",\n'
    "]\n",
    encoding="utf-8",
)

# isolation/__init__.py
(base / "isolation" / "__init__.py").write_text(
    '"""Isolation \u2014 user-scope enforcement via ContextVar + scoped queries."""\n'
    "\n"
    "from agent_sdk.isolation.scope import (\n"
    "    set_user_scope,\n"
    "    get_user_scope,\n"
    "    clear_user_scope,\n"
    "    user_scope,\n"
    ")\n"
    "from agent_sdk.isolation.filter import ScopedQueryBuilder\n"
    "from agent_sdk.isolation.validator import IsolationValidator\n"
    "\n"
    "__all__ = [\n"
    '    "set_user_scope",\n'
    '    "get_user_scope",\n'
    '    "clear_user_scope",\n'
    '    "user_scope",\n'
    '    "ScopedQueryBuilder",\n'
    '    "IsolationValidator",\n'
    "]\n",
    encoding="utf-8",
)

# durability/__init__.py
(base / "durability" / "__init__.py").write_text(
    '"""Durability \u2014 checkpointing, idempotency, replay, recovery."""\n'
    "\n"
    "from agent_sdk.durability.checkpoint import CheckpointManager\n"
    "from agent_sdk.durability.idempotency import IdempotencyTracker\n"
    "from agent_sdk.durability.replay import ReplayEngine, ResumePoint\n"
    "from agent_sdk.durability.recovery import RecoveryManager\n"
    "\n"
    "__all__ = [\n"
    '    "CheckpointManager",\n'
    '    "IdempotencyTracker",\n'
    '    "ReplayEngine",\n'
    '    "RecoveryManager",\n'
    '    "ResumePoint",\n'
    "]\n",
    encoding="utf-8",
)

# governance/__init__.py
(base / "governance" / "__init__.py").write_text(
    '"""Governance \u2014 policy rules, approval workflows, audit logging."""\n'
    "\n"
    "from agent_sdk.governance.policy import PolicyRule\n"
    "from agent_sdk.governance.rules import RuleEngine\n"
    "from agent_sdk.governance.approval import ApprovalManager, ApprovalRequest\n"
    "from agent_sdk.governance.audit import AuditLogger, AuditEntry\n"
    "\n"
    "__all__ = [\n"
    '    "PolicyRule",\n'
    '    "RuleEngine",\n'
    '    "ApprovalManager",\n'
    '    "ApprovalRequest",\n'
    '    "AuditLogger",\n'
    '    "AuditEntry",\n'
    "]\n",
    encoding="utf-8",
)

# persistence/__init__.py
(base / "persistence" / "__init__.py").write_text(
    '"""Persistence \u2014 session store, memory, knowledge, history."""\n'
    "\n"
    "from agent_sdk.persistence.session_store import SessionStore\n"
    "from agent_sdk.persistence.memory import MemoryManager, MemoryEntry\n"
    "from agent_sdk.persistence.knowledge import KnowledgeStore, KnowledgeEntry\n"
    "from agent_sdk.persistence.history import HistoryManager\n"
    "\n"
    "__all__ = [\n"
    '    "SessionStore",\n'
    '    "MemoryManager",\n'
    '    "MemoryEntry",\n'
    '    "KnowledgeStore",\n'
    '    "KnowledgeEntry",\n'
    '    "HistoryManager",\n'
    "]\n",
    encoding="utf-8",
)

# scale/__init__.py
(base / "scale" / "__init__.py").write_text(
    '"""Scale \u2014 retry, circuit breaker, connection pool, queue, rate limiter."""\n'
    "\n"
    "from agent_sdk.scale.retry import RetryPolicy, with_retry, retry\n"
    "from agent_sdk.scale.circuit_breaker import CircuitBreaker\n"
    "from agent_sdk.scale.pool import ConcurrencyPool\n"
    "from agent_sdk.scale.queue import RequestQueue\n"
    "from agent_sdk.scale.rate_limiter import RateLimiter, configure_rate_limits\n"
    "\n"
    "__all__ = [\n"
    '    "RetryPolicy",\n'
    '    "with_retry",\n'
    '    "retry",\n'
    '    "CircuitBreaker",\n'
    '    "ConcurrencyPool",\n'
    '    "RequestQueue",\n'
    '    "RateLimiter",\n'
    '    "configure_rate_limits",\n'
    "]\n",
    encoding="utf-8",
)

# composability/__init__.py
(base / "composability" / "__init__.py").write_text(
    '"""Composability \u2014 server, client, discovery, protocol, MCP."""\n'
    "\n"
    "from agent_sdk.composability.protocol import AgentRequest, AgentResponse\n"
    "from agent_sdk.composability.server import create_agent_app\n"
    "from agent_sdk.composability.client import AgentClient\n"
    "from agent_sdk.composability.discovery import AgentDescriptor, ServiceRegistry\n"
    "from agent_sdk.composability.mcp import MCPAdapter\n"
    "\n"
    "__all__ = [\n"
    '    "AgentRequest",\n'
    '    "AgentResponse",\n'
    '    "create_agent_app",\n'
    '    "AgentClient",\n'
    '    "AgentDescriptor",\n'
    '    "ServiceRegistry",\n'
    '    "MCPAdapter",\n'
    "]\n",
    encoding="utf-8",
)

# Top-level agent_sdk/__init__.py
(base / "__init__.py").write_text(
    '"""agent_sdk \u2014 Production-grade SDK for agentic software."""\n'
    "\n"
    "from agent_sdk._version import __version__\n"
    "from agent_sdk.config import Settings\n"
    "from agent_sdk.types import (\n"
    "    StepStatus,\n"
    "    SessionStatus,\n"
    "    RunStatus,\n"
    "    MessageRole,\n"
    "    ExecutionPolicy,\n"
    "    ApprovalStatus,\n"
    "    MemoryType,\n"
    "    CircuitState,\n"
    ")\n"
    "from agent_sdk.exceptions import (\n"
    "    AgentSDKError,\n"
    "    ConfigurationError,\n"
    "    SessionNotFoundError,\n"
    "    StepExecutionError,\n"
    "    ToolNotFoundError,\n"
    "    ToolExecutionError,\n"
    "    IsolationViolationError,\n"
    "    ApprovalRequiredError,\n"
    "    CheckpointError,\n"
    "    ReplayError,\n"
    "    RateLimitError,\n"
    "    CircuitOpenError,\n"
    "    LLMError,\n"
    "    DiscoveryError,\n"
    ")\n"
    "\n"
    "# Lazy imports for heavy subpackages\n"
    "from agent_sdk.core.agent import Agent\n"
    "from agent_sdk.core.tool import tool\n"
    "\n"
    "__all__ = [\n"
    '    "__version__",\n'
    '    "Settings",\n'
    '    "Agent",\n'
    '    "tool",\n'
    '    # Types\n'
    '    "StepStatus",\n'
    '    "SessionStatus",\n'
    '    "RunStatus",\n'
    '    "MessageRole",\n'
    '    "ExecutionPolicy",\n'
    '    "ApprovalStatus",\n'
    '    "MemoryType",\n'
    '    "CircuitState",\n'
    '    # Exceptions\n'
    '    "AgentSDKError",\n'
    '    "ConfigurationError",\n'
    '    "SessionNotFoundError",\n'
    '    "StepExecutionError",\n'
    '    "ToolNotFoundError",\n'
    '    "ToolExecutionError",\n'
    '    "IsolationViolationError",\n'
    '    "ApprovalRequiredError",\n'
    '    "CheckpointError",\n'
    '    "ReplayError",\n'
    '    "RateLimitError",\n'
    '    "CircuitOpenError",\n'
    '    "LLMError",\n'
    '    "DiscoveryError",\n'
    "]\n",
    encoding="utf-8",
)

print("All __init__.py files written successfully.")
