# Agent SDK — Architecture Plan

> **Project**: agent_sdk  
> **License**: MIT (alikasif, 2026)  
> **Python**: 3.11+  
> **Date**: 2026-03-03  

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Module Breakdown](#2-module-breakdown)
3. [Dependency Map](#3-dependency-map)
4. [API Contracts](#4-api-contracts)
5. [Database Schema](#5-database-schema)
6. [Design Decisions](#6-design-decisions)
7. [Agent Assignments](#7-agent-assignments)
8. [Task Sequencing](#8-task-sequencing)

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Public API Layer                         │
│  (FastAPI service, Agent-to-Agent protocol, MCP interface)      │
├─────────────────────────────────────────────────────────────────┤
│                        Agent Runtime                            │
│  (Agent loop, step execution, tool dispatch, LLM adapter)       │
├──────────┬──────────┬──────────┬──────────┬─────────────────────┤
│ Durability│ Isolation│Governance│Persistence│      Scale         │
│ (ckpt,   │ (user    │ (policy, │ (session, │  (queue, rate      │
│  resume, │  scope,  │  approval│  memory,  │   limit, circuit   │
│  replay) │  filter) │  workflow)│  knowledge│   breaker, pool)   │
├──────────┴──────────┴──────────┴──────────┴─────────────────────┤
│                     Storage Layer (SQLite)                       │
│  (aiosqlite connection pool, migrations, repositories)          │
└─────────────────────────────────────────────────────────────────┘
```

The SDK is organized as a layered architecture. Each pillar (Durability, Isolation, Governance, Persistence, Scale) is a cross-cutting concern implemented as its own module, wired together through the Agent Runtime. The Composability pillar lives at the top as the public API layer.

---

## 2. Module Breakdown

### Package Tree

```
agent_sdk/
├── __init__.py                  # Public re-exports: Agent, Session, Tool, etc.
├── _version.py                  # Single-source version string
│
├── core/                        # Core runtime — the heartbeat of the SDK
│   ├── __init__.py
│   ├── agent.py                 # Agent class: orchestrates step loop, holds config
│   ├── session.py               # Session class: per-user execution context
│   ├── step.py                  # Step model: atomic unit of agent work
│   ├── context.py               # RunContext: request-scoped bag (user_id, session, deps)
│   ├── tool.py                  # Tool base class, registry, and decorator
│   ├── llm.py                   # LLM adapter interface (model provider abstraction)
│   └── message.py               # Message models (user, assistant, tool_call, tool_result)
│
├── durability/                  # Pillar 1 — Checkpoint, pause, resume, recovery
│   ├── __init__.py
│   ├── checkpoint.py            # Checkpoint manager: serialize/restore step state
│   ├── replay.py                # Replay engine: re-execute from checkpoint
│   ├── idempotency.py           # Idempotency key tracking to prevent duplicate side effects
│   └── recovery.py              # Failure detection and automatic resume orchestration
│
├── isolation/                   # Pillar 2 — User boundary enforcement
│   ├── __init__.py
│   ├── scope.py                 # UserScope: attaches user_id to every DB/store operation
│   ├── filter.py                # Query filter injection (auto-adds WHERE user_id = ?)
│   └── validator.py             # Runtime assertions that no cross-user leak occurs
│
├── governance/                  # Pillar 3 — Authority model & approval workflows
│   ├── __init__.py
│   ├── policy.py                # Policy definitions: auto, human_approval, admin_signoff
│   ├── approval.py              # Approval workflow engine (request, wait, resolve)
│   ├── audit.py                 # Audit log: every tool call, decision, approval recorded
│   └── rules.py                 # Rule engine: map tool×context → required authority level
│
├── persistence/                 # Pillar 4 — Sessions, memory, knowledge
│   ├── __init__.py
│   ├── session_store.py         # Session CRUD (create, load, list, archive)
│   ├── memory.py                # Memory manager: short-term (buffer) + long-term (summary)
│   ├── knowledge.py             # Knowledge store: key-value + vector-ready text chunks
│   └── history.py               # Conversation history: append, retrieve, paginate
│
├── scale/                       # Pillar 5 — Concurrency, rate limiting, resilience
│   ├── __init__.py
│   ├── queue.py                 # Async request queue with priority + backpressure
│   ├── rate_limiter.py          # Token-bucket rate limiter (per model provider)
│   ├── circuit_breaker.py       # Circuit breaker for external API calls
│   ├── pool.py                  # Semaphore-based concurrency pool for tool execution
│   └── retry.py                 # Configurable retry with exponential backoff + jitter
│
├── composability/               # Pillar 6 — Agents as services
│   ├── __init__.py
│   ├── server.py                # FastAPI app factory: expose agent as HTTP service
│   ├── client.py                # AgentClient: call remote agents programmatically
│   ├── discovery.py             # Service registry: register/discover agents by name
│   ├── protocol.py              # Agent-to-agent message protocol (request/response schema)
│   └── mcp.py                   # MCP (Model Context Protocol) adapter layer
│
├── db/                          # Storage layer — SQLite via aiosqlite
│   ├── __init__.py
│   ├── connection.py            # Connection pool manager (aiosqlite)
│   ├── migrations.py            # Schema migration runner (versioned, forward-only)
│   ├── repositories/            # Repository pattern — one per domain aggregate
│   │   ├── __init__.py
│   │   ├── session_repo.py      # Sessions table access
│   │   ├── step_repo.py         # Steps/checkpoints table access
│   │   ├── memory_repo.py       # Memory table access
│   │   ├── knowledge_repo.py    # Knowledge table access
│   │   ├── approval_repo.py     # Approval requests table access
│   │   ├── audit_repo.py        # Audit log table access
│   │   └── agent_registry_repo.py  # Agent registry table access
│   └── models.py                # SQLite row ↔ Pydantic model converters
│
├── config.py                    # SDK configuration (Settings via pydantic-settings)
├── exceptions.py                # All custom exceptions in one place
├── types.py                     # Shared type aliases and enums
└── logging.py                   # Structured logging setup (stdlib logging)

tests/
├── conftest.py                  # Shared fixtures (in-memory SQLite, mock LLM, etc.)
├── unit/                        # Fast, isolated unit tests
│   ├── test_agent.py
│   ├── test_session.py
│   ├── test_checkpoint.py
│   ├── test_isolation.py
│   ├── test_governance.py
│   ├── test_memory.py
│   ├── test_queue.py
│   ├── test_rate_limiter.py
│   ├── test_circuit_breaker.py
│   └── ...
├── integration/                 # Tests that touch real SQLite
│   ├── test_durability_flow.py
│   ├── test_session_lifecycle.py
│   ├── test_approval_workflow.py
│   └── ...
└── e2e/                         # End-to-end: spin up FastAPI, run agent, verify
    ├── test_agent_service.py
    └── test_agent_to_agent.py

examples/
├── basic_agent.py               # Minimal agent with one tool
├── durable_agent.py             # Agent with checkpointing demo
├── multi_user.py                # Isolation demo with concurrent users
├── approval_workflow.py         # Governance approval demo
└── agent_service.py             # FastAPI-served agent with discovery
```

### Module Descriptions (one-line each)

| Module | Description |
|--------|-------------|
| `core/agent.py` | Main `Agent` class that owns the step-execution loop and wires all pillars together. |
| `core/session.py` | `Session` represents a single user conversation with its own state and history. |
| `core/step.py` | `Step` is the atomic unit of agent work — a single think→act→observe cycle. |
| `core/context.py` | `RunContext` is the request-scoped dependency bag passed through every layer. |
| `core/tool.py` | Tool definition, registration decorator, and the tool registry. |
| `core/llm.py` | Abstract `LLMAdapter` interface for swapping model providers (OpenAI, Anthropic, etc.). |
| `core/message.py` | Pydantic models for all message types flowing through the agent. |
| `durability/checkpoint.py` | Serializes step state to SQLite and restores it on resume. |
| `durability/replay.py` | Replays completed steps from checkpoints without re-executing side effects. |
| `durability/idempotency.py` | Tracks idempotency keys so tool calls are not duplicated on resume. |
| `durability/recovery.py` | Detects incomplete runs and orchestrates automatic resume. |
| `isolation/scope.py` | Binds `user_id` to the current execution context via contextvars. |
| `isolation/filter.py` | Injects `user_id` filtering into every database query automatically. |
| `isolation/validator.py` | Runtime assertions that results belong to the requesting user. |
| `governance/policy.py` | Defines `ExecutionPolicy` enum and per-tool policy configuration. |
| `governance/approval.py` | Manages approval request lifecycle (pending → approved/denied). |
| `governance/audit.py` | Writes immutable audit log entries for every significant action. |
| `governance/rules.py` | Rule engine that evaluates tool + context → required approval level. |
| `persistence/session_store.py` | CRUD operations for session lifecycle (create, load, list, archive). |
| `persistence/memory.py` | Manages short-term (rolling buffer) and long-term (summarized) agent memory. |
| `persistence/knowledge.py` | Key-value + text-chunk knowledge store for agent reference data. |
| `persistence/history.py` | Append-only conversation history with retrieval and pagination. |
| `scale/queue.py` | Priority async queue with backpressure for incoming requests. |
| `scale/rate_limiter.py` | Token-bucket rate limiter scoped per model provider endpoint. |
| `scale/circuit_breaker.py` | Circuit breaker (closed→open→half-open) for external dependencies. |
| `scale/pool.py` | Semaphore-based concurrency limiter for parallel tool execution. |
| `scale/retry.py` | Retry decorator with exponential backoff, jitter, and configurable limits. |
| `composability/server.py` | FastAPI app factory that exposes any `Agent` as an HTTP service. |
| `composability/client.py` | Async HTTP client to call remote agent services programmatically. |
| `composability/discovery.py` | Service registry for agents to register and discover each other. |
| `composability/protocol.py` | Canonical request/response schemas for agent-to-agent communication. |
| `composability/mcp.py` | Adapter to expose/consume agents via Model Context Protocol. |
| `db/connection.py` | Manages aiosqlite connection pool with proper async lifecycle. |
| `db/migrations.py` | Forward-only migration runner that versions the schema. |
| `db/repositories/*.py` | Repository classes that encapsulate SQL queries per domain entity. |
| `db/models.py` | Pydantic ↔ SQLite row converters (serialization boundary). |
| `config.py` | `Settings` class (pydantic-settings) for all SDK configuration. |
| `exceptions.py` | Custom exception hierarchy for the SDK. |
| `types.py` | Shared enums (`StepStatus`, `ApprovalLevel`, `CircuitState`) and type aliases. |
| `logging.py` | Structured logging configuration using stdlib `logging`. |

---

## 3. Dependency Map

```
                            ┌──────────────┐
                            │  exceptions  │
                            │    types     │
                            │   logging    │
                            │   config     │
                            └──────┬───────┘
                                   │  (used by everything)
                    ┌──────────────┼──────────────┐
                    ▼              ▼               ▼
             ┌────────────┐ ┌───────────┐  ┌──────────────┐
             │  db/       │ │ isolation/ │  │   scale/     │
             │ connection │ │  scope     │  │  retry       │
             │ migrations │ │  filter    │  │  rate_limiter│
             │ models     │ │  validator │  │  circuit_brkr│
             │ repos/*    │ └─────┬─────┘  │  queue       │
             └─────┬──────┘       │        │  pool        │
                   │              │        └──────┬───────┘
                   ▼              ▼               │
          ┌─────────────────────────────┐         │
          │       core/                 │◄────────┘
          │  message, step, tool, llm   │
          │  context, session, agent    │
          └──────┬──────────────────┬───┘
                 │                  │
     ┌───────────┤                  ├───────────┐
     ▼           ▼                  ▼           ▼
┌──────────┐┌──────────┐   ┌────────────┐┌──────────────┐
│durability││governance│   │persistence ││composability │
│checkpoint││ policy   │   │session_stor││  server      │
│ replay   ││ approval │   │  memory    ││  client      │
│idempotenc││  audit   │   │ knowledge  ││  discovery   │
│ recovery ││  rules   │   │  history   ││  protocol    │
└──────────┘└──────────┘   └────────────┘│  mcp         │
                                         └──────────────┘
```

### Explicit Dependencies (import direction: A → B means A imports B)

| Module | Depends On |
|--------|-----------|
| `types.py` | (none — leaf) |
| `exceptions.py` | `types` |
| `logging.py` | (stdlib only) |
| `config.py` | `pydantic-settings` |
| `db/connection.py` | `config`, `aiosqlite` |
| `db/migrations.py` | `db/connection` |
| `db/models.py` | `types`, `pydantic` |
| `db/repositories/*` | `db/connection`, `db/models`, `isolation/filter` |
| `isolation/scope.py` | `types` (uses `contextvars`) |
| `isolation/filter.py` | `isolation/scope` |
| `isolation/validator.py` | `isolation/scope`, `exceptions` |
| `scale/retry.py` | `config`, `exceptions` |
| `scale/rate_limiter.py` | `config`, `asyncio` |
| `scale/circuit_breaker.py` | `config`, `types`, `exceptions` |
| `scale/queue.py` | `asyncio`, `types` |
| `scale/pool.py` | `asyncio`, `config` |
| `core/message.py` | `types`, `pydantic` |
| `core/step.py` | `core/message`, `types`, `pydantic` |
| `core/tool.py` | `core/context`, `types`, `pydantic` |
| `core/llm.py` | `core/message`, `types` |
| `core/context.py` | `isolation/scope`, `config`, `db/connection` |
| `core/session.py` | `core/context`, `core/step`, `persistence/*`, `durability/*` |
| `core/agent.py` | `core/*`, `governance/*`, `scale/*`, `durability/*` |
| `durability/checkpoint.py` | `core/step`, `db/repositories/step_repo` |
| `durability/replay.py` | `durability/checkpoint`, `core/step` |
| `durability/idempotency.py` | `db/repositories/step_repo` |
| `durability/recovery.py` | `durability/checkpoint`, `durability/replay`, `core/session` |
| `governance/policy.py` | `types`, `pydantic` |
| `governance/rules.py` | `governance/policy`, `core/tool` |
| `governance/approval.py` | `governance/policy`, `db/repositories/approval_repo` |
| `governance/audit.py` | `db/repositories/audit_repo`, `core/context` |
| `persistence/session_store.py` | `db/repositories/session_repo`, `core/session` |
| `persistence/memory.py` | `db/repositories/memory_repo`, `core/context` |
| `persistence/knowledge.py` | `db/repositories/knowledge_repo` |
| `persistence/history.py` | `db/repositories/session_repo`, `core/message` |
| `composability/protocol.py` | `core/message`, `pydantic` |
| `composability/server.py` | `core/agent`, `composability/protocol`, `fastapi` |
| `composability/client.py` | `composability/protocol`, `httpx` |
| `composability/discovery.py` | `db/repositories/agent_registry_repo`, `config` |
| `composability/mcp.py` | `composability/protocol`, `core/tool` |

---

## 4. API Contracts

### 4.1 Core

```python
# ── core/agent.py ──────────────────────────────────────────────

class Agent:
    """Top-level orchestrator. One Agent instance per agent definition."""

    def __init__(
        self,
        name: str,
        instructions: str | Callable[[RunContext], str],
        tools: list[Tool] = [],
        llm: LLMAdapter | None = None,
        settings: Settings | None = None,
        policies: list[PolicyRule] = [],
    ) -> None: ...

    async def run(
        self,
        user_id: str,
        input: str | list[Message],
        *,
        session_id: str | None = None,   # None = new session
        max_steps: int = 30,
        resume: bool = False,             # resume from last checkpoint
    ) -> AgentResult: ...

    async def stream(
        self,
        user_id: str,
        input: str | list[Message],
        *,
        session_id: str | None = None,
        max_steps: int = 30,
    ) -> AsyncIterator[StreamEvent]: ...

    def tool(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        policy: ExecutionPolicy = ExecutionPolicy.AUTO,
    ) -> Callable[[Callable[..., Any]], Tool]: ...
        """Decorator to register a tool on this agent."""

    async def initialize(self) -> None: ...
        """Run DB migrations, warm caches, verify connectivity."""

    async def shutdown(self) -> None: ...
        """Graceful shutdown: drain queue, flush checkpoints, close DB."""


class AgentResult(BaseModel):
    session_id: str
    user_id: str
    messages: list[Message]
    steps: list[Step]
    final_output: str
    status: RunStatus               # completed | paused | failed
    resumed_from_step: int | None
```

```python
# ── core/session.py ─────────────────────────────────────────────

class Session:
    """Encapsulates a single conversation for one user."""

    id: str                         # UUID
    user_id: str
    agent_name: str
    created_at: datetime
    updated_at: datetime
    status: SessionStatus           # active | paused | completed | archived
    metadata: dict[str, Any]

    async def add_message(self, message: Message) -> None: ...
    async def get_history(self, limit: int = 50, before: datetime | None = None) -> list[Message]: ...
    async def get_steps(self) -> list[Step]: ...
    async def pause(self) -> None: ...
    async def resume(self) -> None: ...
    async def archive(self) -> None: ...
```

```python
# ── core/step.py ────────────────────────────────────────────────

class Step(BaseModel):
    """Atomic unit of agent work: one think→act→observe cycle."""

    id: str                         # UUID
    session_id: str
    step_number: int                # 1-based ordinal within the session
    status: StepStatus              # pending | running | completed | failed | skipped
    input_messages: list[Message]
    output_message: Message | None
    tool_calls: list[ToolCall]
    tool_results: list[ToolResult]
    checkpoint: bytes | None        # serialized state for resume
    idempotency_key: str            # for deduplication on replay
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
```

```python
# ── core/context.py ─────────────────────────────────────────────

class RunContext:
    """Request-scoped dependency bag threaded through every call."""

    user_id: str
    session: Session
    agent: Agent
    db: DatabaseConnection
    settings: Settings

    def get_scoped_repo[T: Repository](self, repo_class: type[T]) -> T: ...
        """Returns a repository already filtered to self.user_id."""
```

```python
# ── core/tool.py ────────────────────────────────────────────────

class Tool(BaseModel):
    name: str
    description: str
    parameters_schema: dict[str, Any]    # JSON Schema from Pydantic model
    policy: ExecutionPolicy
    fn: Callable[..., Awaitable[Any]]    # the actual async callable

    async def execute(self, ctx: RunContext, **kwargs: Any) -> ToolResult: ...

class ToolCall(BaseModel):
    id: str
    tool_name: str
    arguments: dict[str, Any]

class ToolResult(BaseModel):
    tool_call_id: str
    output: Any
    error: str | None
    idempotency_key: str

class ToolRegistry:
    def register(self, tool: Tool) -> None: ...
    def get(self, name: str) -> Tool: ...
    def list_tools(self) -> list[Tool]: ...
    def to_schemas(self) -> list[dict[str, Any]]: ...
        """Export as OpenAI-style function schemas for the LLM."""
```

```python
# ── core/llm.py ─────────────────────────────────────────────────

class LLMAdapter(ABC):
    """Abstract interface — implement per model provider."""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse: ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[LLMChunk]: ...

class LLMResponse(BaseModel):
    message: Message
    tool_calls: list[ToolCall]
    usage: TokenUsage

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
```

```python
# ── core/message.py ─────────────────────────────────────────────

class Message(BaseModel):
    role: MessageRole                # user | assistant | system | tool
    content: str | None
    tool_calls: list[ToolCall] | None
    tool_call_id: str | None         # set when role=tool
    name: str | None
    timestamp: datetime
    metadata: dict[str, Any] = {}
```

### 4.2 Durability

```python
# ── durability/checkpoint.py ────────────────────────────────────

class CheckpointManager:
    def __init__(self, step_repo: StepRepository) -> None: ...

    async def save(self, step: Step) -> None: ...
        """Serialize and persist the step's complete state."""

    async def load(self, session_id: str, step_number: int) -> Step | None: ...
        """Restore a step from its checkpoint."""

    async def load_latest(self, session_id: str) -> Step | None: ...
        """Get the last completed checkpoint for a session."""

    async def list_checkpoints(self, session_id: str) -> list[StepSummary]: ...


# ── durability/replay.py ───────────────────────────────────────

class ReplayEngine:
    def __init__(self, checkpoint_mgr: CheckpointManager, idempotency: IdempotencyTracker) -> None: ...

    async def replay_to(self, session_id: str, step_number: int) -> list[Step]: ...
        """Replay steps 1..N from checkpoints (no re-execution)."""

    async def resume_from(self, session_id: str) -> ResumePoint: ...
        """Find the last clean checkpoint and prepare for resumption."""

class ResumePoint(BaseModel):
    session_id: str
    resume_step: int
    replayed_steps: list[Step]
    pending_messages: list[Message]


# ── durability/idempotency.py ──────────────────────────────────

class IdempotencyTracker:
    async def record(self, key: str, result: ToolResult) -> None: ...
    async def check(self, key: str) -> ToolResult | None: ...
        """Returns cached result if this key was already executed."""
    async def clear(self, session_id: str) -> None: ...


# ── durability/recovery.py ─────────────────────────────────────

class RecoveryManager:
    async def detect_incomplete(self) -> list[str]: ...
        """Return session_ids with uncompleted runs."""

    async def auto_resume(self, session_id: str, agent: Agent) -> AgentResult: ...
        """Automatically resume an incomplete session."""
```

### 4.3 Isolation

```python
# ── isolation/scope.py ─────────────────────────────────────────

# Uses contextvars for zero-cost propagation through async callstack.
_current_user_id: ContextVar[str]

def set_user_scope(user_id: str) -> Token: ...
def get_user_scope() -> str: ...
def clear_user_scope(token: Token) -> None: ...

@contextlib.asynccontextmanager
async def user_scope(user_id: str) -> AsyncIterator[None]: ...
    """Context manager that sets + clears user scope."""


# ── isolation/filter.py ────────────────────────────────────────

class ScopedQueryBuilder:
    """Wraps SQL queries to inject user_id filtering."""

    def select(self, table: str, where: dict[str, Any] = {}, **kwargs) -> tuple[str, list]: ...
    def insert(self, table: str, values: dict[str, Any]) -> tuple[str, list]: ...
    def update(self, table: str, set_: dict[str, Any], where: dict[str, Any] = {}) -> tuple[str, list]: ...
    def delete(self, table: str, where: dict[str, Any] = {}) -> tuple[str, list]: ...
        """All methods auto-inject user_id from current scope."""


# ── isolation/validator.py ─────────────────────────────────────

class IsolationValidator:
    @staticmethod
    def assert_owns(record: dict[str, Any], expected_user_id: str) -> None: ...
        """Raises IsolationViolationError if user_id doesn't match."""

    @staticmethod
    def assert_all_owned(records: list[dict[str, Any]], expected_user_id: str) -> None: ...
```

### 4.4 Governance

```python
# ── governance/policy.py ───────────────────────────────────────

class ExecutionPolicy(str, Enum):
    AUTO = "auto"                      # Execute immediately
    HUMAN_APPROVAL = "human_approval"  # Require human approval
    ADMIN_SIGNOFF = "admin_signoff"    # Require admin approval

class PolicyRule(BaseModel):
    tool_name: str | None              # None = wildcard
    policy: ExecutionPolicy
    condition: str | None              # optional SpEL/CEL-like expression
    description: str


# ── governance/approval.py ─────────────────────────────────────

class ApprovalRequest(BaseModel):
    id: str
    session_id: str
    user_id: str
    step_number: int
    tool_call: ToolCall
    required_policy: ExecutionPolicy
    status: ApprovalStatus             # pending | approved | denied | expired
    requested_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
    reason: str | None

class ApprovalManager:
    async def request_approval(self, ctx: RunContext, tool_call: ToolCall, policy: ExecutionPolicy) -> ApprovalRequest: ...
    async def resolve(self, request_id: str, decision: ApprovalStatus, resolved_by: str, reason: str = "") -> ApprovalRequest: ...
    async def get_pending(self, user_id: str | None = None) -> list[ApprovalRequest]: ...
    async def wait_for_resolution(self, request_id: str, timeout: float = 300.0) -> ApprovalRequest: ...


# ── governance/audit.py ────────────────────────────────────────

class AuditEntry(BaseModel):
    id: str
    timestamp: datetime
    user_id: str
    session_id: str
    action: str                        # tool_executed, approval_requested, etc.
    details: dict[str, Any]

class AuditLogger:
    async def log(self, ctx: RunContext, action: str, details: dict[str, Any]) -> None: ...
    async def query(self, user_id: str | None = None, action: str | None = None, since: datetime | None = None, limit: int = 100) -> list[AuditEntry]: ...


# ── governance/rules.py ────────────────────────────────────────

class RuleEngine:
    def __init__(self, rules: list[PolicyRule]) -> None: ...
    def evaluate(self, tool: Tool, ctx: RunContext) -> ExecutionPolicy: ...
        """Return the highest required authority level for this tool+context."""
```

### 4.5 Persistence

```python
# ── persistence/session_store.py ───────────────────────────────

class SessionStore:
    async def create(self, user_id: str, agent_name: str, metadata: dict = {}) -> Session: ...
    async def load(self, session_id: str) -> Session: ...
    async def list_sessions(self, user_id: str, status: SessionStatus | None = None, limit: int = 20) -> list[Session]: ...
    async def update_status(self, session_id: str, status: SessionStatus) -> None: ...
    async def archive(self, session_id: str) -> None: ...
    async def delete(self, session_id: str) -> None: ...


# ── persistence/memory.py ──────────────────────────────────────

class MemoryManager:
    """Two-tier memory: short-term buffer + long-term summaries."""

    async def add_short_term(self, ctx: RunContext, key: str, value: str) -> None: ...
    async def get_short_term(self, ctx: RunContext, limit: int = 10) -> list[MemoryEntry]: ...

    async def add_long_term(self, ctx: RunContext, key: str, value: str, tags: list[str] = []) -> None: ...
    async def search_long_term(self, ctx: RunContext, query: str, limit: int = 5) -> list[MemoryEntry]: ...

    async def summarize_and_promote(self, ctx: RunContext) -> None: ...
        """Summarize short-term buffer into long-term storage."""

    async def clear(self, ctx: RunContext) -> None: ...

class MemoryEntry(BaseModel):
    id: str
    user_id: str
    session_id: str | None
    key: str
    value: str
    memory_type: MemoryType          # short_term | long_term
    tags: list[str]
    created_at: datetime


# ── persistence/knowledge.py ───────────────────────────────────

class KnowledgeStore:
    async def put(self, user_id: str, namespace: str, key: str, content: str, metadata: dict = {}) -> None: ...
    async def get(self, user_id: str, namespace: str, key: str) -> KnowledgeEntry | None: ...
    async def search(self, user_id: str, namespace: str, query: str, limit: int = 10) -> list[KnowledgeEntry]: ...
    async def delete(self, user_id: str, namespace: str, key: str) -> None: ...
    async def list_namespaces(self, user_id: str) -> list[str]: ...

class KnowledgeEntry(BaseModel):
    user_id: str
    namespace: str
    key: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ── persistence/history.py ─────────────────────────────────────

class HistoryManager:
    async def append(self, session_id: str, message: Message) -> None: ...
    async def get(self, session_id: str, limit: int = 50, before: datetime | None = None) -> list[Message]: ...
    async def get_full(self, session_id: str) -> list[Message]: ...
    async def count(self, session_id: str) -> int: ...
    async def truncate(self, session_id: str, keep_last: int) -> None: ...
```

### 4.6 Scale

```python
# ── scale/queue.py ─────────────────────────────────────────────

class RequestQueue:
    def __init__(self, max_size: int = 1000, max_workers: int = 10) -> None: ...

    async def submit(self, request: AgentRequest, priority: int = 0) -> str: ...
        """Returns a request_id. Raises BackpressureError if full."""

    async def get_result(self, request_id: str, timeout: float = 300.0) -> AgentResult: ...
    async def cancel(self, request_id: str) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    @property
    def pending_count(self) -> int: ...
    @property
    def active_count(self) -> int: ...


# ── scale/rate_limiter.py ──────────────────────────────────────

class RateLimiter:
    def __init__(self, rate: float, burst: int, name: str = "default") -> None: ...

    async def acquire(self, tokens: int = 1) -> None: ...
        """Block until tokens are available."""

    def try_acquire(self, tokens: int = 1) -> bool: ...
        """Non-blocking check."""

    @property
    def available_tokens(self) -> float: ...


# ── scale/circuit_breaker.py ───────────────────────────────────

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max: int = 1,
    ) -> None: ...

    @property
    def state(self) -> CircuitState: ...    # closed | open | half_open

    async def call[T](self, fn: Callable[..., Awaitable[T]], *args, **kwargs) -> T: ...
        """Execute fn through the circuit breaker."""

    def record_success(self) -> None: ...
    def record_failure(self) -> None: ...
    def reset(self) -> None: ...


# ── scale/pool.py ──────────────────────────────────────────────

class ConcurrencyPool:
    def __init__(self, max_concurrent: int = 10) -> None: ...

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]: ...

    async def run[T](self, fn: Callable[..., Awaitable[T]], *args, **kwargs) -> T: ...
    async def gather(self, tasks: list[Callable[..., Awaitable[Any]]]) -> list[Any]: ...

    @property
    def active(self) -> int: ...
    @property
    def available(self) -> int: ...


# ── scale/retry.py ─────────────────────────────────────────────

class RetryPolicy(BaseModel):
    max_retries: int = 3
    base_delay: float = 1.0         # seconds
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)

async def with_retry[T](
    fn: Callable[..., Awaitable[T]],
    policy: RetryPolicy = RetryPolicy(),
    *args,
    **kwargs,
) -> T: ...

def retry(policy: RetryPolicy = RetryPolicy()) -> Callable: ...
    """Decorator form."""
```

### 4.7 Composability

```python
# ── composability/server.py ────────────────────────────────────

def create_agent_app(
    agent: Agent,
    *,
    prefix: str = "/agent",
    enable_discovery: bool = True,
    cors_origins: list[str] = ["*"],
) -> FastAPI: ...
    """Factory that mounts agent endpoints onto a FastAPI app."""

# Endpoints created:
#   POST   {prefix}/run              — Run agent (request/response)
#   POST   {prefix}/stream           — Run agent (SSE stream)
#   GET    {prefix}/sessions/{id}    — Get session details
#   GET    {prefix}/sessions         — List sessions for user
#   POST   {prefix}/sessions/{id}/resume — Resume paused session
#   GET    {prefix}/approvals        — List pending approvals
#   POST   {prefix}/approvals/{id}   — Resolve an approval
#   GET    {prefix}/health           — Health check
#   GET    {prefix}/schema           — Agent capability schema (OpenAPI)


# ── composability/client.py ────────────────────────────────────

class AgentClient:
    def __init__(self, base_url: str, timeout: float = 300.0) -> None: ...

    async def run(self, user_id: str, input: str, session_id: str | None = None) -> AgentResult: ...
    async def stream(self, user_id: str, input: str) -> AsyncIterator[StreamEvent]: ...
    async def get_session(self, session_id: str) -> Session: ...
    async def list_sessions(self, user_id: str) -> list[Session]: ...
    async def resume(self, session_id: str) -> AgentResult: ...
    async def resolve_approval(self, request_id: str, decision: str, reason: str = "") -> ApprovalRequest: ...
    async def health(self) -> dict[str, Any]: ...

    async def close(self) -> None: ...
    async def __aenter__(self) -> AgentClient: ...
    async def __aexit__(self, *exc) -> None: ...


# ── composability/discovery.py ─────────────────────────────────

class AgentDescriptor(BaseModel):
    name: str
    description: str
    base_url: str
    tools: list[str]
    version: str
    registered_at: datetime
    health_url: str

class ServiceRegistry:
    async def register(self, descriptor: AgentDescriptor) -> None: ...
    async def deregister(self, name: str) -> None: ...
    async def discover(self, name: str) -> AgentDescriptor | None: ...
    async def list_agents(self) -> list[AgentDescriptor]: ...
    async def health_check_all(self) -> dict[str, bool]: ...


# ── composability/protocol.py ──────────────────────────────────

class AgentRequest(BaseModel):
    user_id: str
    input: str | list[Message]
    session_id: str | None = None
    max_steps: int = 30
    metadata: dict[str, Any] = {}

class AgentResponse(BaseModel):
    session_id: str
    user_id: str
    output: str
    messages: list[Message]
    status: RunStatus
    usage: TokenUsage | None

class StreamEvent(BaseModel):
    event: str                       # step_start, token, tool_call, tool_result, step_end, done, error
    data: dict[str, Any]


# ── composability/mcp.py ──────────────────────────────────────

class MCPAdapter:
    """Expose agent tools as MCP resources, or consume MCP tools."""

    def __init__(self, agent: Agent) -> None: ...

    def to_mcp_tools(self) -> list[dict[str, Any]]: ...
        """Export agent tools in MCP schema format."""

    async def handle_mcp_call(self, tool_name: str, arguments: dict) -> dict: ...
        """Handle an incoming MCP tool invocation."""

    async def call_mcp_tool(self, server_url: str, tool_name: str, arguments: dict) -> Any: ...
        """Call a remote MCP server's tool."""
```

### 4.8 Database

```python
# ── db/connection.py ───────────────────────────────────────────

class DatabaseConnection:
    def __init__(self, db_path: str = "agent_sdk.db", pool_size: int = 5) -> None: ...

    async def initialize(self) -> None: ...
        """Create pool, enable WAL mode, run migrations."""

    async def execute(self, sql: str, params: list[Any] = []) -> aiosqlite.Cursor: ...
    async def fetch_one(self, sql: str, params: list[Any] = []) -> dict[str, Any] | None: ...
    async def fetch_all(self, sql: str, params: list[Any] = []) -> list[dict[str, Any]]: ...
    async def execute_many(self, sql: str, params_list: list[list[Any]]) -> None: ...

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]: ...
        """Atomic transaction boundary."""

    async def close(self) -> None: ...


# ── db/migrations.py ───────────────────────────────────────────

class MigrationRunner:
    def __init__(self, db: DatabaseConnection) -> None: ...
    async def run(self) -> None: ...
        """Apply all pending migrations in order."""
    async def current_version(self) -> int: ...
```

---

## 5. Database Schema

### Schema Version Table

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);
```

### Sessions

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,                  -- UUID
    user_id     TEXT NOT NULL,
    agent_name  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',    -- active|paused|completed|archived
    metadata    TEXT NOT NULL DEFAULT '{}',        -- JSON
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(user_id, status);
```

### Messages (Conversation History)

```sql
CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,              -- UUID
    session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id         TEXT NOT NULL,
    role            TEXT NOT NULL,                 -- user|assistant|system|tool
    content         TEXT,
    tool_calls      TEXT,                          -- JSON array of ToolCall
    tool_call_id    TEXT,
    name            TEXT,
    metadata        TEXT NOT NULL DEFAULT '{}',    -- JSON
    timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
    ordinal         INTEGER NOT NULL               -- message order within session
);
CREATE INDEX idx_messages_session ON messages(session_id, ordinal);
CREATE INDEX idx_messages_user ON messages(user_id);
```

### Steps (Checkpoints / Durability)

```sql
CREATE TABLE IF NOT EXISTS steps (
    id              TEXT PRIMARY KEY,              -- UUID
    session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id         TEXT NOT NULL,
    step_number     INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending', -- pending|running|completed|failed|skipped
    input_messages  TEXT NOT NULL DEFAULT '[]',    -- JSON
    output_message  TEXT,                          -- JSON
    tool_calls      TEXT NOT NULL DEFAULT '[]',    -- JSON
    tool_results    TEXT NOT NULL DEFAULT '[]',    -- JSON
    checkpoint      BLOB,                          -- serialized state (msgpack/pickle)
    idempotency_key TEXT NOT NULL,
    error           TEXT,
    started_at      TEXT,
    completed_at    TEXT,
    UNIQUE(session_id, step_number)
);
CREATE INDEX idx_steps_session ON steps(session_id, step_number);
CREATE INDEX idx_steps_user ON steps(user_id);
CREATE INDEX idx_steps_idempotency ON steps(idempotency_key);
```

### Idempotency Keys

```sql
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key         TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id     TEXT NOT NULL,
    result      TEXT NOT NULL,                     -- JSON-serialized ToolResult
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_idempotency_session ON idempotency_keys(session_id);
```

### Memory

```sql
CREATE TABLE IF NOT EXISTS memory (
    id          TEXT PRIMARY KEY,                  -- UUID
    user_id     TEXT NOT NULL,
    session_id  TEXT,                              -- NULL for cross-session long-term memory
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    memory_type TEXT NOT NULL,                     -- short_term | long_term
    tags        TEXT NOT NULL DEFAULT '[]',        -- JSON array
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_memory_user ON memory(user_id, memory_type);
CREATE INDEX idx_memory_session ON memory(session_id);
CREATE INDEX idx_memory_user_key ON memory(user_id, key);
```

### Knowledge

```sql
CREATE TABLE IF NOT EXISTS knowledge (
    user_id     TEXT NOT NULL,
    namespace   TEXT NOT NULL,
    key         TEXT NOT NULL,
    content     TEXT NOT NULL,
    metadata    TEXT NOT NULL DEFAULT '{}',        -- JSON
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, namespace, key)
);
CREATE INDEX idx_knowledge_user_ns ON knowledge(user_id, namespace);
```

### Approvals (Governance)

```sql
CREATE TABLE IF NOT EXISTS approvals (
    id              TEXT PRIMARY KEY,              -- UUID
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    user_id         TEXT NOT NULL,
    step_number     INTEGER NOT NULL,
    tool_name       TEXT NOT NULL,
    tool_arguments  TEXT NOT NULL,                 -- JSON
    required_policy TEXT NOT NULL,                 -- human_approval | admin_signoff
    status          TEXT NOT NULL DEFAULT 'pending', -- pending|approved|denied|expired
    requested_at    TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at     TEXT,
    resolved_by     TEXT,
    reason          TEXT
);
CREATE INDEX idx_approvals_user ON approvals(user_id, status);
CREATE INDEX idx_approvals_session ON approvals(session_id);
```

### Audit Log

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id          TEXT PRIMARY KEY,                  -- UUID
    timestamp   TEXT NOT NULL DEFAULT (datetime('now')),
    user_id     TEXT NOT NULL,
    session_id  TEXT,
    action      TEXT NOT NULL,
    details     TEXT NOT NULL DEFAULT '{}',        -- JSON
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_time ON audit_log(timestamp);
```

### Agent Registry (Composability)

```sql
CREATE TABLE IF NOT EXISTS agent_registry (
    name            TEXT PRIMARY KEY,
    description     TEXT NOT NULL,
    base_url        TEXT NOT NULL,
    tools           TEXT NOT NULL DEFAULT '[]',    -- JSON array of tool names
    version         TEXT NOT NULL,
    health_url      TEXT NOT NULL,
    registered_at   TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Schema Notes

- **All tables with `user_id`**: Every query through `ScopedQueryBuilder` automatically appends `WHERE user_id = ?` to enforce isolation.
- **JSON columns**: Stored as `TEXT` with JSON serialization. SQLite's `json_extract()` is available for queries.
- **Timestamps**: Stored as ISO-8601 `TEXT` for SQLite compatibility and human readability.
- **UUIDs**: Generated as `uuid4().hex` strings, stored as `TEXT`.
- **Checkpoint BLOB**: Step state serialized via `msgpack` (preferred for speed) with `pickle` fallback.
- **WAL mode**: Enabled at connection initialization for concurrent read performance.

---

## 6. Design Decisions

### D1: Async-First with `asyncio`

**Choice**: All SDK APIs are `async/await`. Synchronous wrappers are not provided in v1.

**Rationale**: Agents are I/O-bound (LLM calls, tool calls, DB ops). Async allows serving thousands of concurrent sessions without threads. `aiosqlite` provides async SQLite access. All modern Python web frameworks (FastAPI) are async-native.

### D2: Checkpoint Strategy — Step-Level Granularity

**Choice**: Checkpoint after every completed step (think→act→observe cycle). The checkpoint contains the full step state including input messages, output, tool calls, and tool results.

**Rationale**: Step-level granularity gives the best balance of recovery precision vs. storage cost. Sub-step checkpointing (e.g., mid-LLM-call) is complex and offers little benefit since LLM calls are idempotent. The checkpoint is saved inside a DB transaction along with the step status update, making it atomic.

**Recovery flow**:
1. On resume, load all completed steps from DB
2. Replay their outputs into the message history (no re-execution)
3. Resume execution from the first incomplete step
4. Idempotency keys prevent re-executing tool calls that may have completed before the crash

### D3: Isolation via `contextvars` + Query Injection

**Choice**: `user_id` is stored in a `ContextVar` set at the start of every `agent.run()` call. `ScopedQueryBuilder` auto-injects `user_id` into every SQL query. `IsolationValidator` double-checks returned rows.

**Rationale**: `ContextVar` propagates automatically through the async callstack — no need to pass `user_id` explicitly to every function. This makes the isolation enforcement automatic and hard to accidentally bypass. The validator provides defense-in-depth. Three layers:
1. **ContextVar** — scope is set once, propagated everywhere
2. **Query injection** — SQL always filters by user_id  
3. **Validator** — post-hoc assertion on returned data

### D4: Governance via Policy Rules + Async Approval Queue

**Choice**: Each tool is tagged with an `ExecutionPolicy`. A `RuleEngine` evaluates tool + context to determine the required authority level. If approval is needed, the step pauses, an approval request is persisted to DB, and execution suspends. An external system (or human via API) resolves the approval. The agent resumes.

**Rationale**: This cleanly separates policy definition from execution. Policies can be defined declaratively. The approval workflow uses the same pause/resume machinery as durability, avoiding duplication. The audit log captures everything for compliance.

### D5: Connection Pool via Queue of `aiosqlite` Connections

**Choice**: Maintain a pool of N `aiosqlite` connections. Operations acquire a connection from the pool and return it when done.

**Rationale**: While SQLite is single-writer, WAL mode allows concurrent reads. A pool prevents connection starvation under load. `aiosqlite` wraps each connection in a background thread, so the pool also acts as a thread pool.

### D6: Pydantic for All Data Models

**Choice**: Every data structure (messages, steps, config, API request/response) is a Pydantic `BaseModel`.

**Rationale**: Provides validation, serialization (JSON, dict), type safety, and automatic OpenAPI schema generation for the FastAPI layer. Pydantic v2 is fast enough that no optimization is needed.

### D7: Repository Pattern for DB Access

**Choice**: One repository class per domain aggregate (sessions, steps, memory, knowledge, approvals, audit). Repositories consume `DatabaseConnection` and `ScopedQueryBuilder`.

**Rationale**: Isolates SQL from business logic. Makes it easy to test (swap repository with mock). Provides a clear place to enforce isolation filtering.

### D8: Serialization Format for Checkpoints — `msgpack` with JSON Fallback

**Choice**: Step checkpoints are serialized with `msgpack` for compact binary storage. A JSON fallback is available for debugging.

**Rationale**: `msgpack` is 2-5x smaller and faster than JSON for binary data. Checkpoints can contain large message histories. The JSON fallback aids debugging during development.

### D9: FastAPI for Composability Layer

**Choice**: FastAPI as the HTTP framework. Each agent is exposed as a service via a factory function that mounts standard endpoints.

**Rationale**: FastAPI is the standard for async Python APIs. It generates OpenAPI docs automatically (enabling discovery). SSE streaming is well-supported. Pydantic integration is native.

### D10: Retry + Circuit Breaker at the Scale Layer

**Choice**: External calls (LLM, tools) are wrapped in `RetryPolicy` and `CircuitBreaker`. These are composable: `circuit_breaker.call(with_retry(fn, policy))`.

**Rationale**: LLM APIs are unreliable. Rate limits, timeouts, and 5xx errors are common. The circuit breaker prevents thundering-herd retries against a degraded service. These are generic enough to apply to any external dependency.

### D11: Agent-to-Agent Communication via HTTP + Shared Protocol

**Choice**: Agents communicate via the same HTTP protocol used by external clients. `AgentClient` is a thin async HTTP client. No custom RPC.

**Rationale**: HTTP is universally accessible (Slack bots, frontends, other agents all speak HTTP). Using the same protocol for all consumers simplifies the system. Service discovery is handled by the `ServiceRegistry`.

### D12: Minimal External Dependencies

**Choice**: Core dependencies are limited to:
- `pydantic` (v2) — data models and validation
- `pydantic-settings` — configuration management
- `aiosqlite` — async SQLite
- `msgpack` — checkpoint serialization
- `fastapi` — HTTP service layer (optional, only for composability)
- `uvicorn` — ASGI server (optional, only for composability)
- `httpx` — async HTTP client (optional, only for agent-to-agent)

**Rationale**: Fewer dependencies = fewer CVEs, fewer conflicts, faster installs. The SDK uses the Python standard library for asyncio, logging, contextvars, uuid, datetime, json, and typing.

---

## 7. Agent Assignments

Each specialist agent is responsible for a vertical slice of the implementation.

| Agent | Responsibility | Modules |
|-------|---------------|---------|
| **`python_coder_core`** | Core runtime: Agent, Session, Step, Context, Tool, Message, LLM | `core/*`, `types.py`, `exceptions.py`, `config.py`, `logging.py`, `__init__.py` |
| **`python_coder_db`** | Database layer: connection pool, migrations, all repositories | `db/*` |
| **`python_coder_durability`** | Checkpoint, replay, idempotency, recovery | `durability/*` |
| **`python_coder_isolation`** | User scope, query filter injection, isolation validator | `isolation/*` |
| **`python_coder_governance`** | Policy, approval workflow, audit log, rule engine | `governance/*` |
| **`python_coder_persistence`** | Session store, memory manager, knowledge store, history | `persistence/*` |
| **`python_coder_scale`** | Queue, rate limiter, circuit breaker, pool, retry | `scale/*` |
| **`python_coder_composability`** | FastAPI server, client, discovery, protocol, MCP | `composability/*` |
| **`python_test`** | All tests: unit, integration, e2e | `tests/*` |
| **`documentation`** | README, API docs, examples, ARCHITECTURE.md maintenance | `README.md`, `examples/*`, `docs/*` |
| **`devops`** | `pyproject.toml`, CI/CD, linting config, packaging | `pyproject.toml`, `.github/*`, `ruff.toml` |

---

## 8. Task Sequencing

### Phase 0: Project Scaffolding
**Dependencies**: None  
**Agent**: `devops`  
**Tasks**:
1. Create `pyproject.toml` with project metadata, dependencies, dev dependencies
2. Create package structure (all `__init__.py` files)
3. Create `ruff.toml` for linting config
4. Create `conftest.py` with base fixtures

### Phase 1: Foundation Layer
**Dependencies**: Phase 0  
**Agents**: `python_coder_core`, `python_coder_db`  
**Tasks** (can be parallelized):
1. **`types.py`** — All enums: `StepStatus`, `SessionStatus`, `RunStatus`, `MessageRole`, `ExecutionPolicy`, `ApprovalStatus`, `MemoryType`, `CircuitState`
2. **`exceptions.py`** — Full exception hierarchy
3. **`config.py`** — `Settings` class with all configuration
4. **`logging.py`** — Structured logging setup
5. **`core/message.py`** — `Message`, `ToolCall`, `ToolResult` models
6. **`db/connection.py`** — `DatabaseConnection` with pool, WAL, transactions
7. **`db/migrations.py`** — `MigrationRunner` + all SQL table definitions
8. **`db/models.py`** — Row ↔ Pydantic converters

### Phase 2: Isolation Layer
**Dependencies**: Phase 1  
**Agent**: `python_coder_isolation`  
**Tasks**:
1. **`isolation/scope.py`** — `ContextVar`-based user scope
2. **`isolation/filter.py`** — `ScopedQueryBuilder`
3. **`isolation/validator.py`** — `IsolationValidator`

### Phase 3: Repositories
**Dependencies**: Phase 1, Phase 2  
**Agent**: `python_coder_db`  
**Tasks**:
1. **`db/repositories/session_repo.py`** — Sessions CRUD
2. **`db/repositories/step_repo.py`** — Steps/checkpoints CRUD
3. **`db/repositories/memory_repo.py`** — Memory CRUD
4. **`db/repositories/knowledge_repo.py`** — Knowledge CRUD
5. **`db/repositories/approval_repo.py`** — Approvals CRUD
6. **`db/repositories/audit_repo.py`** — Audit log CRUD
7. **`db/repositories/agent_registry_repo.py`** — Agent registry CRUD

### Phase 4: Core Runtime
**Dependencies**: Phase 3  
**Agent**: `python_coder_core`  
**Tasks**:
1. **`core/tool.py`** — `Tool`, `ToolRegistry`, `@tool` decorator
2. **`core/llm.py`** — `LLMAdapter` ABC, `LLMResponse`, `TokenUsage`
3. **`core/step.py`** — `Step` model
4. **`core/context.py`** — `RunContext`
5. **`core/session.py`** — `Session` with full lifecycle
6. **`core/agent.py`** — `Agent` with step loop (initially without durability/governance hooks)

### Phase 5: Pillar Implementations (parallelizable)
**Dependencies**: Phase 4  

**5a — Durability** (`python_coder_durability`):
1. `durability/checkpoint.py`
2. `durability/idempotency.py`
3. `durability/replay.py`
4. `durability/recovery.py`
5. Wire into `core/agent.py` step loop

**5b — Governance** (`python_coder_governance`):
1. `governance/policy.py`
2. `governance/rules.py`
3. `governance/approval.py`
4. `governance/audit.py`
5. Wire into `core/agent.py` tool dispatch

**5c — Persistence** (`python_coder_persistence`):
1. `persistence/history.py`
2. `persistence/session_store.py`
3. `persistence/memory.py`
4. `persistence/knowledge.py`

**5d — Scale** (`python_coder_scale`):
1. `scale/retry.py`
2. `scale/rate_limiter.py`
3. `scale/circuit_breaker.py`
4. `scale/pool.py`
5. `scale/queue.py`

### Phase 6: Composability
**Dependencies**: Phase 5 (all)  
**Agent**: `python_coder_composability`  
**Tasks**:
1. `composability/protocol.py`
2. `composability/server.py`
3. `composability/client.py`
4. `composability/discovery.py`
5. `composability/mcp.py`

### Phase 7: Integration & Wiring
**Dependencies**: Phase 6  
**Agents**: `python_coder_core`, `python_test`  
**Tasks**:
1. Wire all pillars into `Agent.run()` / `Agent.stream()`
2. Complete `__init__.py` public re-exports
3. Write integration tests for full agent lifecycle
4. Write e2e tests for HTTP service

### Phase 8: Documentation & Examples
**Dependencies**: Phase 7  
**Agent**: `documentation`  
**Tasks**:
1. Complete `README.md` with quickstart, installation, concepts
2. Write example scripts (`examples/*.py`)
3. Add docstrings to all public APIs
4. Generate API reference docs

### Dependency Graph (Visual)

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──┐
                                                             │
                                          ┌─── 5a Durability ◄──┐
                                          ├─── 5b Governance ◄──┤
                                          ├─── 5c Persistence ◄─┼── Phase 5
                                          └─── 5d Scale ◄───────┘
                                                   │
                                                   ▼
                                             Phase 6 (Composability)
                                                   │
                                                   ▼
                                             Phase 7 (Integration)
                                                   │
                                                   ▼
                                             Phase 8 (Docs)
```

---

## Appendix A: `pyproject.toml` Skeleton

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "agent-sdk"
version = "0.1.0"
description = "A Python Agent SDK with durability, isolation, governance, persistence, scale, and composability."
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [{ name = "alikasif" }]

dependencies = [
    "pydantic>=2.5,<3",
    "pydantic-settings>=2.1,<3",
    "aiosqlite>=0.19,<1",
    "msgpack>=1.0,<2",
]

[project.optional-dependencies]
server = [
    "fastapi>=0.109,<1",
    "uvicorn[standard]>=0.27,<1",
    "httpx>=0.26,<1",
]
all = ["agent-sdk[server]"]
dev = [
    "pytest>=8.0,<9",
    "pytest-asyncio>=0.23,<1",
    "pytest-cov>=4.1,<6",
    "ruff>=0.2,<1",
    "mypy>=1.8,<2",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.11"
strict = true
```

---

## Appendix B: Exception Hierarchy

```python
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
```

---

## Appendix C: Key Flows

### C1: Normal Agent Run

```
1. Agent.run(user_id, input, session_id=None)
2.   → Set user_scope(user_id) via ContextVar
3.   → Create or load Session (via SessionStore)
4.   → Append user message to history
5.   → LOOP (max_steps):
6.      a. Build message list from history + memory
7.      b. Call LLM via LLMAdapter.chat()
8.      c. If LLM returns tool_calls:
9.         i.   For each tool_call:
10.            - RuleEngine.evaluate(tool, ctx) → policy
11.            - If policy == AUTO → execute tool
12.            - If policy == HUMAN_APPROVAL → ApprovalManager.request_approval()
13.              → Pause session, save checkpoint, return paused result
14.            - Record idempotency key + result
15.            - AuditLogger.log()
16.         ii.  Append tool results to messages
17.      d. Else (no tool_calls) → final output
18.      e. Save step checkpoint to DB
19.   → Return AgentResult
```

### C2: Resume After Crash

```
1. Agent.run(user_id, input=None, session_id="...", resume=True)
2.   → Set user_scope(user_id)
3.   → Load Session
4.   → ReplayEngine.resume_from(session_id)
5.      → Load all completed steps from DB
6.      → Rebuild message history from checkpoints (no re-execution)
7.      → Return ResumePoint(resume_step=12, replayed_steps=[1..11])
8.   → Continue LOOP from step 12
9.      → For any tool_call, check idempotency key first
10.     → If key exists, use cached result (no re-execution)
11.     → If key missing, execute normally
12.  → Return AgentResult
```

### C3: Approval Workflow

```
1. Agent step loop calls delete_customer_record tool
2. RuleEngine.evaluate() → HUMAN_APPROVAL
3. ApprovalManager.request_approval() → creates pending ApprovalRequest in DB
4. AuditLogger.log("approval_requested", ...)
5. Session status → paused, step checkpoint saved
6. Agent.run() returns AgentResult(status=paused)
7. --- External: Human reviews via API ---
8. POST /agent/approvals/{id} {decision: "approved", reason: "verified"}
9. ApprovalManager.resolve() → updates DB
10. Agent.run(session_id=..., resume=True) → resumes from paused step
11. Tool executes, result recorded, flow continues
```

---

*End of architecture plan. This document drives implementation across all phases.*
