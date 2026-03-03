"""Tool system: Tool model, ToolRegistry, and @tool decorator."""

from __future__ import annotations

import inspect
import functools
from typing import Any, Callable, Awaitable, get_type_hints
from uuid import uuid4

from pydantic import BaseModel, Field

from agent_sdk.types import ExecutionPolicy
from agent_sdk.exceptions import ToolNotFoundError, ToolExecutionError
from agent_sdk.core.message import ToolCall, ToolResult


class Tool(BaseModel):
    """A registered tool that an agent can invoke."""

    model_config = {"arbitrary_types_allowed": True}

    name: str
    description: str = ""
    parameters_schema: dict[str, Any] = Field(default_factory=dict)
    policy: ExecutionPolicy = ExecutionPolicy.AUTO
    fn: Callable[..., Awaitable[Any]] = Field(exclude=True)

    async def execute(self, ctx: Any, **kwargs: Any) -> ToolResult:
        """Run the tool function and return a ToolResult."""
        call_id = uuid4().hex
        try:
            sig = inspect.signature(self.fn)
            if "ctx" in sig.parameters or "context" in sig.parameters:
                result = await self.fn(ctx, **kwargs)
            else:
                result = await self.fn(**kwargs)
            return ToolResult(tool_call_id=call_id, output=result)
        except Exception as exc:
            raise ToolExecutionError(f"Tool '{self.name}' failed: {exc}") from exc


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def to_schemas(self) -> list[dict[str, Any]]:
        """Export as OpenAI-style function schemas for the LLM."""
        schemas: list[dict[str, Any]] = []
        for t in self._tools.values():
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters_schema or {"type": "object", "properties": {}},
                    },
                }
            )
        return schemas


def _build_schema_from_hints(fn: Callable[..., Any]) -> dict[str, Any]:
    """Auto-generate a JSON Schema from function type hints."""
    hints = get_type_hints(fn)
    sig = inspect.signature(fn)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("ctx", "context", "self", "cls"):
            continue
        hint = hints.get(param_name, Any)

        # Check if it's a Pydantic model
        if isinstance(hint, type) and issubclass(hint, BaseModel):
            properties[param_name] = hint.model_json_schema()
        else:
            properties[param_name] = _type_to_schema(hint)

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _type_to_schema(hint: Any) -> dict[str, Any]:
    """Convert a Python type annotation to a JSON Schema snippet."""
    origin = getattr(hint, "__origin__", None)
    if hint is str:
        return {"type": "string"}
    if hint is int:
        return {"type": "integer"}
    if hint is float:
        return {"type": "number"}
    if hint is bool:
        return {"type": "boolean"}
    if origin is list:
        args = getattr(hint, "__args__", ())
        items = _type_to_schema(args[0]) if args else {}
        return {"type": "array", "items": items}
    if origin is dict:
        return {"type": "object"}
    return {"type": "string"}


def tool(
    _fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    policy: ExecutionPolicy = ExecutionPolicy.AUTO,
) -> Any:
    """Decorator to turn an async function into an agent Tool.

    Supports both ``@tool`` and ``@tool(name=..., description=...)`` syntax.
    """

    def _wrap(fn: Callable[..., Any]) -> Tool:
        tool_name = name or fn.__name__
        tool_desc = description or (fn.__doc__ or "").strip()
        schema = _build_schema_from_hints(fn)

        t = Tool(
            name=tool_name,
            description=tool_desc,
            parameters_schema=schema,
            policy=policy,
            fn=fn,
        )
        # Preserve original function metadata
        functools.update_wrapper(t, fn)  # type: ignore[arg-type]
        return t

    if _fn is not None:
        # Called as @tool without parentheses
        return _wrap(_fn)
    return _wrap
