# Project Name: agent_sdk

> **Date**: 2026-03-03
> **Python**: 3.11+
> **Database**: SQLite (aiosqlite)
> **License**: MIT

---

## Git Strategy

- **Branch**: `feature/agent-sdk-core`
- **Base**: `main`
- **First commit**: Scaffold with project structure, pyproject.toml, Dockerfile

---

## Overview

A Python Agent SDK that provides six pillars for production-grade agentic software:

1. **Durability** — Checkpoint, pause, resume, recover. Crash at step 12? Resume from step 12.
2. **Isolation** — Every user gets their own session, memory, context. Enforced at every layer.
3. **Governance** — Layered authority: auto-execute, human-approval, admin-sign-off. Audit everything.
4. **Persistence** — Sessions, memory, knowledge stored in SQLite. Every conversation improves the next.
5. **Scale** — Async execution, request queuing, rate limiting, circuit breakers for external dependencies.
6. **Composability** — Agents as FastAPI services. Agent-to-agent communication. MCP compatibility.

---

## Technology Stack

| Concern | Technology | Notes |
|---------|-----------|-------|
| Language | Python 3.11+ | Async-first |
| LLM Calls | **litellm** | 100+ providers via unified API |
| Database | SQLite via **aiosqlite** | WAL mode, async access |
| Data Models | **Pydantic** v2 | Validation, serialization, JSON Schema generation |
| API Layer | **FastAPI** + **uvicorn** | Composability/service layer |
| HTTP Client | **httpx** | Agent-to-agent communication |
| Serialization | **msgpack** | Checkpoint serialization |
| Rate Limiting | **litellm built-in** | RPM/TPM per model |
| Queuing | asyncio.Queue + SQLite persistence | No external broker |
| Sessions | SDK-managed in SQLite | Scoped by user_id |
| Tools | `@tool` decorator | Auto-schema from type hints + Pydantic |
| Container | **Docker Desktop** | Dockerfile + docker-compose.yml |
| Testing | pytest + pytest-asyncio | Unit, integration, e2e |
| Linting | ruff + mypy | Strict type checking |

---

## Module Architecture

```
agent_sdk/
├── __init__.py              # Public re-exports
├── _version.py              # Version string
├── config.py                # Settings (pydantic-settings)
├── exceptions.py            # Exception hierarchy
├── types.py                 # Enums and type aliases
├── logging.py               # Structured logging
│
├── core/                    # Agent runtime
│   ├── agent.py             # Agent class + step loop
│   ├── session.py           # Session lifecycle
│   ├── step.py              # Step model (atomic work unit)
│   ├── context.py           # RunContext (request-scoped)
│   ├── tool.py              # @tool decorator, ToolRegistry
│   ├── llm.py               # litellm adapter
│   └── message.py           # Message models
│
├── durability/              # Checkpoint, replay, recovery
│   ├── checkpoint.py
│   ├── replay.py
│   ├── idempotency.py
│   └── recovery.py
│
├── isolation/               # User boundary enforcement
│   ├── scope.py             # ContextVar-based user scope
│   ├── filter.py            # ScopedQueryBuilder
│   └── validator.py         # IsolationValidator
│
├── governance/              # Policy, approval, audit
│   ├── policy.py
│   ├── rules.py
│   ├── approval.py
│   └── audit.py
│
├── persistence/             # Sessions, memory, knowledge
│   ├── session_store.py
│   ├── memory.py
│   ├── knowledge.py
│   └── history.py
│
├── scale/                   # Concurrency, resilience
│   ├── queue.py
│   ├── rate_limiter.py
│   ├── circuit_breaker.py
│   ├── pool.py
│   └── retry.py
│
├── composability/           # Agent-as-service
│   ├── server.py            # FastAPI factory
│   ├── client.py            # AgentClient
│   ├── discovery.py         # ServiceRegistry
│   ├── protocol.py          # Request/response schemas
│   └── mcp.py               # MCP adapter
│
└── db/                      # SQLite storage layer
    ├── connection.py         # Connection pool
    ├── migrations.py         # Schema migrations
    ├── models.py             # Row ↔ Pydantic converters
    └── repositories/
        ├── session_repo.py
        ├── step_repo.py
        ├── memory_repo.py
        ├── knowledge_repo.py
        ├── approval_repo.py
        ├── audit_repo.py
        └── agent_registry_repo.py
```

---

## Database Schema

9 SQLite tables: `schema_version`, `sessions`, `messages`, `steps`, `idempotency_keys`, `memory`, `knowledge`, `approvals`, `audit_log`, `agent_registry`

All tables with `user_id` are auto-filtered by `ScopedQueryBuilder` for isolation. Full schema in ARCHITECTURE.md §5.

---

## Key Design Decisions

1. **Async-first** — All APIs are async/await. No sync wrappers in v1.
2. **Step-level checkpoints** — Checkpoint after every step. Atomic with DB transaction.
3. **Triple-layer isolation** — ContextVar → query injection → post-hoc validation.
4. **Declarative governance** — Policy rules evaluated per tool+context. Approval pauses agent.
5. **litellm for LLM calls** — Unified API, 100+ providers, built-in rate limiting.
6. **@tool decorator** — Functions become tools. Type hints → JSON Schema automatically.
7. **Repository pattern** — SQL isolated from business logic. All repos use ScopedQueryBuilder.
8. **Docker Desktop** — Dockerfile + docker-compose.yml for containerized deployment.

---

## API Contracts

Full API contracts (classes, methods, signatures) are defined in ARCHITECTURE.md §4. Key surfaces:

- `Agent(name, instructions, tools, model)` → `.run()`, `.stream()`, `.tool()`
- `Session` → `.add_message()`, `.get_history()`, `.pause()`, `.resume()`
- `@tool(description, governance)` → decorator for tool functions
- `create_agent_app(agent)` → FastAPI app factory
- `AgentClient(base_url)` → remote agent caller

---

## Implementation Phases

### Phase 0: Scaffold
Project structure, pyproject.toml, Docker, configs.

### Phase 1: Foundation
types.py, exceptions.py, config.py, logging.py, message models, DB connection, migrations.

### Phase 2: Isolation
ContextVar scope, ScopedQueryBuilder, IsolationValidator.

### Phase 3: Repositories
All 7 repository classes using ScopedQueryBuilder.

### Phase 4: Core Runtime
Tool system, LLM adapter (litellm), Step, Context, Session, Agent.

### Phase 5: Pillars (parallel)
5a: Durability — checkpoint, replay, idempotency, recovery
5b: Governance — policy, rules, approval, audit
5c: Persistence — session store, memory, knowledge, history
5d: Scale — retry, circuit breaker, pool, queue

### Phase 6: Composability
Protocol, FastAPI server, client, discovery, MCP.

### Phase 7: Integration
Wire all pillars into Agent.run(), public __init__.py, integration tests, e2e tests.

### Phase 8: Documentation & DevOps
README, examples, API docs, CI/CD, Docker finalization.

---

## GitHub Details

- **Repository**: agent_sdk (existing)
- **Branch**: `feature/agent-sdk-core`
- **PR Title**: "feat: Agent SDK with durability, isolation, governance, persistence, scale, composability"
