"""Unit tests for agent_sdk.core.message models."""
import pytest
from agent_sdk.core.message import Message, ToolCall, ToolResult
from agent_sdk.types import MessageRole
import json

def test_toolcall_model():
    tc = ToolCall(tool_name="math", arguments={"x": 1, "y": 2})
    assert tc.tool_name == "math"
    assert tc.arguments == {"x": 1, "y": 2}
    assert isinstance(tc.id, str)

def test_toolresult_model():
    tr = ToolResult(tool_call_id="abc123", output=42, error=None)
    assert tr.tool_call_id == "abc123"
    assert tr.output == 42
    assert tr.error is None
    assert isinstance(tr.idempotency_key, str)

def test_message_model():
    msg = Message(role=MessageRole.USER, content="Hello", tool_calls=None)
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello"
    assert msg.tool_calls is None
    assert isinstance(msg.timestamp, type(msg.timestamp))
    assert isinstance(msg.metadata, dict)

def test_serialization_roundtrip():
    tc = ToolCall(tool_name="math", arguments={"x": 1})
    tr = ToolResult(tool_call_id=tc.id, output=3)
    msg = Message(role=MessageRole.TOOL, content=None, tool_calls=[tc], tool_call_id=tc.id)
    d = msg.model_dump()
    j = json.dumps(d, default=str)
    loaded = Message.model_validate(json.loads(j))
    assert loaded.role == MessageRole.TOOL
    assert loaded.tool_calls[0].tool_name == "math"
    assert loaded.tool_call_id == tc.id
