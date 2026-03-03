# Agent SDK


A Python Agent SDK for building robust, multi-user agents with durability, isolation, governance, persistence, scale, and composability.

## Overview

Agent SDK is a layered, async-first Python framework for building agents that can:
- Persist and recover state (durability)
- Enforce user boundaries (isolation)
- Support approval workflows and audit logging (governance)
- Store sessions, memory, and knowledge (persistence)
- Handle concurrency, rate limits, and resilience (scale)
- Expose agents as HTTP services (composability)

See [ARCHITECTURE.md](ARCHITECTURE.md) for full details.

## Key Features

- **Async-first**: All APIs use async/await for high concurrency
- **Durability**: Step-level checkpointing and recovery
- **Isolation**: ContextVar-based user scoping and query injection
- **Governance**: Policy rules, approval workflows, audit log
- **Persistence**: Session, memory, knowledge, and history managers
- **Scale**: Request queue, rate limiter, circuit breaker, concurrency pool, retry
- **Composability**: FastAPI server, agent client, service discovery, shared protocol

## Architecture

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

## Module Structure

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full breakdown. Major modules:

- `core/`: Agent, Session, Step, Context, Tool, LLM, Message
- `durability/`: Checkpoint, replay, idempotency, recovery
- `isolation/`: User scope, query filter, validator
- `governance/`: Policy, approval, audit, rules
- `persistence/`: Session store, memory, knowledge, history
- `scale/`: Queue, rate limiter, circuit breaker, pool, retry
- `composability/`: FastAPI server, client, discovery, protocol, MCP
- `db/`: Connection pool, migrations, repositories, models

## Design Decisions

- **Async everywhere**: All SDK APIs are async/await for scalability
- **Step-level checkpointing**: Durable recovery after every agent step
- **User isolation**: Enforced via ContextVar and query injection
- **Governance**: Policy rules and async approval queue
- **Repository pattern**: One class per domain aggregate
- **Minimal dependencies**: Only pydantic, aiosqlite, msgpack, fastapi, httpx, uvicorn

## Quickstart

Install dependencies:

```bash
pip install agent-sdk
```

Create a minimal agent:

```python
from agent_sdk.core import Agent

agent = Agent(name="demo-agent")

# Register a tool
@agent.tool()
async def echo(ctx, text: str) -> str:
    return text

# Run the agent
result = await agent.run(user_id="user1", input="Hello!")
print(result.final_output)
```

## Project Phases

Implementation is organized into phases:

1. Project scaffolding
2. Foundation layer (types, exceptions, config, logging, core models, db)
3. Isolation layer
4. Repositories
5. Core runtime
6. Pillar implementations (durability, governance, persistence, scale)
7. Composability (HTTP server/client, protocol)
8. Integration & wiring
9. Documentation & examples

See [ARCHITECTURE.md](ARCHITECTURE.md) for details and sequencing.

## License

MIT (c) alikasif, 2026
