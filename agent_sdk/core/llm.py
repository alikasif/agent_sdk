"""LLM adapter interface and litellm implementation."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from agent_sdk.core.message import (
    LLMResponse,
    Message,
    StreamEvent,
    TokenUsage,
    ToolCall,
)
from agent_sdk.exceptions import LLMError
from agent_sdk.types import MessageRole

logger = logging.getLogger("agent_sdk.llm")


class LLMAdapter(ABC):
    """Abstract interface for LLM providers."""

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
    ) -> AsyncIterator[StreamEvent]: ...


def _messages_to_dicts(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert SDK Message list to litellm-compatible dicts."""
    result: list[dict[str, Any]] = []
    for msg in messages:
        d: dict[str, Any] = {"role": msg.role.value, "content": msg.content}
        if msg.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.tool_name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in msg.tool_calls
            ]
        if msg.tool_call_id:
            d["tool_call_id"] = msg.tool_call_id
        if msg.name:
            d["name"] = msg.name
        result.append(d)
    return result


def _parse_tool_calls(raw_tool_calls: list[Any] | None) -> list[ToolCall]:
    """Parse tool_calls from litellm response into ToolCall models."""
    if not raw_tool_calls:
        return []
    import json as _json

    calls: list[ToolCall] = []
    for tc in raw_tool_calls:
        fn = tc.function if hasattr(tc, "function") else tc.get("function", {})
        fn_name = fn.name if hasattr(fn, "name") else fn.get("name", "")
        fn_args_raw = fn.arguments if hasattr(fn, "arguments") else fn.get("arguments", "{}")
        try:
            fn_args = _json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
        except _json.JSONDecodeError:
            fn_args = {}
        call_id = tc.id if hasattr(tc, "id") else tc.get("id", "")
        calls.append(ToolCall(id=call_id, tool_name=fn_name, arguments=fn_args))
    return calls


class LiteLLMAdapter(LLMAdapter):
    """LLM adapter backed by litellm."""

    def __init__(self, model: str, api_key: str | None = None, **kwargs: Any) -> None:
        self.model = model
        self.api_key = api_key
        self.extra_kwargs = kwargs

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        try:
            import litellm

            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": _messages_to_dicts(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
                **self.extra_kwargs,
            }
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if tools:
                kwargs["tools"] = tools

            response = await litellm.acompletion(**kwargs)
            choice = response.choices[0]
            raw_msg = choice.message

            tool_calls = _parse_tool_calls(getattr(raw_msg, "tool_calls", None))

            message = Message(
                role=MessageRole.ASSISTANT,
                content=getattr(raw_msg, "content", None),
                tool_calls=tool_calls or None,
            )

            usage_obj = getattr(response, "usage", None)
            usage = TokenUsage(
                prompt_tokens=getattr(usage_obj, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage_obj, "completion_tokens", 0) or 0,
                total_tokens=getattr(usage_obj, "total_tokens", 0) or 0,
            )

            return LLMResponse(message=message, tool_calls=tool_calls, usage=usage)
        except Exception as exc:
            if isinstance(exc, LLMError):
                raise
            raise LLMError(f"LLM call failed: {exc}") from exc

    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        try:
            import litellm

            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": _messages_to_dicts(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
                **self.extra_kwargs,
            }
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if tools:
                kwargs["tools"] = tools

            response = await litellm.acompletion(**kwargs)
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta:
                    if getattr(delta, "content", None):
                        yield StreamEvent(event="token", data={"content": delta.content})
                    if getattr(delta, "tool_calls", None):
                        yield StreamEvent(
                            event="tool_call",
                            data={"tool_calls": [tc.model_dump() if hasattr(tc, "model_dump") else tc for tc in delta.tool_calls]},
                        )
            yield StreamEvent(event="done", data={})
        except Exception as exc:
            if isinstance(exc, LLMError):
                raise
            raise LLMError(f"LLM stream failed: {exc}") from exc
