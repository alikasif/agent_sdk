"""Composability — server, client, discovery, protocol, MCP."""

from agent_sdk.composability.protocol import AgentRequest, AgentResponse
from agent_sdk.composability.server import create_agent_app
from agent_sdk.composability.client import AgentClient
from agent_sdk.composability.discovery import AgentDescriptor, ServiceRegistry
from agent_sdk.composability.mcp import MCPAdapter

__all__ = [
    "AgentRequest",
    "AgentResponse",
    "create_agent_app",
    "AgentClient",
    "AgentDescriptor",
    "ServiceRegistry",
    "MCPAdapter",
]
