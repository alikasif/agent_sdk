"""AgentClient — async HTTP client to call remote agent services."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

logger = logging.getLogger("agent_sdk.composability.client")


class AgentClient:
    """Async HTTP client for calling remote agent services."""

    def __init__(self, base_url: str, timeout: float = 300.0) -> None:
        if not _HAS_HTTPX:
            raise ImportError("httpx is required. Install with: pip install agent-sdk[server]")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def run(
        self,
        user_id: str,
        input: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Call the agent's /run endpoint."""
        client = self._get_client()
        payload: dict[str, Any] = {"user_id": user_id, "input": input}
        if session_id:
            payload["session_id"] = session_id
        response = await client.post("/agent/run", json=payload)
        response.raise_for_status()
        return response.json()

    async def stream(
        self, user_id: str, input: str
    ) -> AsyncIterator[dict[str, Any]]:
        """Call the agent's /stream SSE endpoint."""
        import json
        client = self._get_client()
        async with client.stream(
            "POST", "/agent/stream", json={"user_id": user_id, "input": input}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield json.loads(line[6:])

    async def get_session(self, session_id: str, user_id: str = "") -> dict[str, Any]:
        """Get session details."""
        client = self._get_client()
        response = await client.get(
            f"/agent/sessions/{session_id}", params={"user_id": user_id}
        )
        response.raise_for_status()
        return response.json()

    async def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """List sessions for a user."""
        client = self._get_client()
        response = await client.get("/agent/sessions", params={"user_id": user_id})
        response.raise_for_status()
        return response.json()

    async def resume(self, session_id: str, user_id: str = "") -> dict[str, Any]:
        """Resume a paused session."""
        client = self._get_client()
        response = await client.post(
            f"/agent/sessions/{session_id}/resume",
            params={"user_id": user_id},
        )
        response.raise_for_status()
        return response.json()

    async def resolve_approval(
        self, request_id: str, decision: str, reason: str = "", user_id: str = ""
    ) -> dict[str, Any]:
        """Resolve an approval."""
        client = self._get_client()
        response = await client.post(
            f"/agent/approvals/{request_id}",
            params={"user_id": user_id, "decision": decision, "reason": reason},
        )
        response.raise_for_status()
        return response.json()

    async def health(self) -> dict[str, Any]:
        """Health check."""
        client = self._get_client()
        response = await client.get("/agent/health")
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> AgentClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
