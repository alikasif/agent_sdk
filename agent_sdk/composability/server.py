"""FastAPI app factory — expose any Agent as an HTTP service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any, TYPE_CHECKING

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False

from agent_sdk.composability.protocol import AgentRequest, AgentResponse
from agent_sdk.exceptions import SessionNotFoundError, AgentSDKError
from agent_sdk.types import ApprovalStatus, RunStatus

if TYPE_CHECKING:
    from agent_sdk.core.agent import Agent

logger = logging.getLogger("agent_sdk.composability.server")


def create_agent_app(
    agent: Agent,
    *,
    prefix: str = "/agent",
    enable_discovery: bool = True,
    cors_origins: list[str] | None = None,
) -> Any:
    """Factory that mounts agent endpoints onto a FastAPI app."""
    if not _HAS_FASTAPI:
        raise ImportError(
            "FastAPI is required for the composability server. "
            "Install with: pip install agent-sdk[server]"
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await agent.initialize()
        yield
        await agent.shutdown()

    app = FastAPI(title=f"Agent: {agent.name}", version="0.1.0", lifespan=lifespan)

    # CORS
    origins = cors_origins or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post(f"{prefix}/run")
    async def run(request: AgentRequest) -> AgentResponse:
        """Run agent (request/response)."""
        try:
            input_val: str | list = request.input  # type: ignore[assignment]
            result = await agent.run(
                user_id=request.user_id,
                input=input_val,
                session_id=request.session_id,
                max_steps=request.max_steps,
            )
            return AgentResponse(
                session_id=result.session_id,
                user_id=result.user_id,
                output=result.final_output,
                messages=result.messages,
                status=result.status,
            )
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except AgentSDKError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post(f"{prefix}/stream")
    async def stream(request: AgentRequest) -> StreamingResponse:
        """Run agent (SSE stream)."""
        import json

        async def event_generator():
            try:
                input_val: str | list = request.input  # type: ignore[assignment]
                async for event in agent.stream(
                    user_id=request.user_id,
                    input=input_val,
                    session_id=request.session_id,
                    max_steps=request.max_steps,
                ):
                    yield f"data: {json.dumps(event.model_dump())}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'event': 'error', 'data': {'error': str(exc)}})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.get(f"{prefix}/sessions/{{session_id}}")
    async def get_session(session_id: str, user_id: str) -> dict[str, Any]:
        """Get session details."""
        from agent_sdk.isolation.scope import set_user_scope, clear_user_scope
        from agent_sdk.db.repositories.session_repo import SessionRepository

        token = set_user_scope(user_id)
        try:
            assert agent._db is not None
            repo = SessionRepository(agent._db)
            row = await repo.get_by_id(session_id)
            if not row:
                raise HTTPException(status_code=404, detail="Session not found.")
            return dict(row)
        finally:
            clear_user_scope(token)

    @app.get(f"{prefix}/sessions")
    async def list_sessions(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """List sessions for user."""
        from agent_sdk.isolation.scope import set_user_scope, clear_user_scope
        from agent_sdk.db.repositories.session_repo import SessionRepository

        token = set_user_scope(user_id)
        try:
            assert agent._db is not None
            repo = SessionRepository(agent._db)
            return await repo.list_by_user(limit=limit)
        finally:
            clear_user_scope(token)

    @app.post(f"{prefix}/sessions/{{session_id}}/resume")
    async def resume_session(session_id: str, user_id: str) -> AgentResponse:
        """Resume a paused session."""
        try:
            result = await agent.run(
                user_id=user_id,
                input=None,
                session_id=session_id,
                resume=True,
            )
            return AgentResponse(
                session_id=result.session_id,
                user_id=result.user_id,
                output=result.final_output,
                messages=result.messages,
                status=result.status,
            )
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except AgentSDKError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get(f"{prefix}/approvals")
    async def list_approvals(user_id: str) -> list[dict[str, Any]]:
        """List pending approvals."""
        from agent_sdk.isolation.scope import set_user_scope, clear_user_scope
        from agent_sdk.db.repositories.approval_repo import ApprovalRepository

        token = set_user_scope(user_id)
        try:
            assert agent._db is not None
            repo = ApprovalRepository(agent._db)
            return await repo.get_pending()
        finally:
            clear_user_scope(token)

    @app.post(f"{prefix}/approvals/{{approval_id}}")
    async def resolve_approval(
        approval_id: str,
        user_id: str,
        decision: str = "approved",
        reason: str = "",
    ) -> dict[str, str]:
        """Resolve an approval."""
        from agent_sdk.isolation.scope import set_user_scope, clear_user_scope
        from agent_sdk.db.repositories.approval_repo import ApprovalRepository

        token = set_user_scope(user_id)
        try:
            assert agent._db is not None
            repo = ApprovalRepository(agent._db)
            await repo.resolve(
                approval_id=approval_id,
                status=decision,
                resolved_by=user_id,
                reason=reason,
            )
            return {"status": "resolved", "approval_id": approval_id}
        finally:
            clear_user_scope(token)

    @app.get(f"{prefix}/health")
    async def health() -> dict[str, str]:
        """Health check."""
        return {"status": "healthy", "agent": agent.name}

    @app.get(f"{prefix}/schema")
    async def schema() -> dict[str, Any]:
        """Agent capability schema."""
        tools = agent._registry.to_schemas()
        return {
            "name": agent.name,
            "tools": tools,
            "version": "0.1.0",
        }

    return app
