"""Unit tests for agent_sdk.core.tool and @tool decorator."""
import pytest
from agent_sdk.core.tool import Tool, ToolRegistry, tool
from agent_sdk.types import ExecutionPolicy


@pytest.mark.asyncio
async def test_tool_decorator_basic():
    @tool
    async def greet(name: str) -> str:
        return f"Hello, {name}!"
    # @tool already returns a Tool instance
    assert isinstance(greet, Tool)
    assert greet.name == "greet"
    result = await greet.execute(None, name="World")
    assert result.output == "Hello, World!"


@pytest.mark.asyncio
async def test_tool_decorator_with_args():
    @tool(description="Add numbers")
    async def add(x: int, y: int) -> int:
        return x + y
    assert isinstance(add, Tool)
    assert add.description == "Add numbers"
    result = await add.execute(None, x=2, y=3)
    assert result.output == 5


@pytest.mark.asyncio
async def test_tool_json_schema_generation():
    @tool
    async def echo(text: str, flag: bool, value: float, count: int) -> str:
        return f"{text}-{flag}-{value}-{count}"
    assert isinstance(echo, Tool)
    schema = echo.parameters_schema
    assert "properties" in schema
    assert schema["properties"]["text"]["type"] == "string"
    assert schema["properties"]["flag"]["type"] == "boolean"
    assert schema["properties"]["value"]["type"] == "number"
    assert schema["properties"]["count"]["type"] == "integer"


@pytest.mark.asyncio
async def test_tool_registry_register_get_list():
    reg = ToolRegistry()
    @tool
    async def foo(x: int) -> int:
        return x * 2
    reg.register(foo)  # foo is already a Tool
    assert reg.get("foo") is foo
    assert reg.list_tools() == [foo]
    schemas = reg.to_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "foo"


@pytest.mark.asyncio
async def test_tool_decorator_syntax_variants():
    @tool
    async def a(x: int) -> int:
        return x
    @tool()
    async def b(y: int) -> int:
        return y
    assert isinstance(a, Tool)
    assert isinstance(b, Tool)
    assert a.name == "a"
    assert b.name == "b"
