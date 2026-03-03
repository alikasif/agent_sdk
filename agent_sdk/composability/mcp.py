"""MCP (Model Context Protocol) adapter layer."""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agent_sdk.core.agent import Agent

logger = logging.getLogger("agent_sdk.composability.mcp")


class MCPAdapter:
    """Expose agent tools as MCP resources, or consume MCP tools."""

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    def to_mcp_tools(self) -> list[dict[str, Any]]:
        """Export agent tools in MCP schema format."""
        mcp_tools: list[dict[str, Any]] = []
        for tool in self._agent._registry.list_tools():
            mcp_tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.parameters_schema,
            })
        return mcp_tools

    async def handle_mcp_call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle an incoming MCP tool invocation."""
        from agent_sdk.core.tool import ToolResult
        from agent_sdk.exceptions import ToolNotFoundError

        try:
            tool = self._agent._registry.get(tool_name)
        except ToolNotFoundError:
            return {"error": f"Tool '{tool_name}' not found."}

        try:
            result: ToolResult = await tool.execute(None, **arguments)
            return {
                "tool_call_id": result.tool_call_id,
                "output": result.output,
                "error": result.error,
            }
        except Exception as exc:
            return {"error": str(exc)}

    async def call_mcp_tool(
        self,
        server_url: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Call a remote MCP server's tool."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{server_url.rstrip('/')}/tools/{tool_name}",
                    json=arguments,
                )
                response.raise_for_status()
                return response.json()
        except ImportError:
            raise ImportError("httpx is required for MCP remote calls.")
        except Exception as exc:
            logger.error("MCP remote call failed: %s", exc)
            raise
