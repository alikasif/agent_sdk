"""Unit tests for agent_sdk.exceptions hierarchy."""
import pytest
import agent_sdk.exceptions as exc

def test_exception_hierarchy():
    base = exc.AgentSDKError("base error")
    assert isinstance(base, Exception)
    # All custom exceptions inherit from AgentSDKError
    for name in dir(exc):
        obj = getattr(exc, name)
        if isinstance(obj, type) and issubclass(obj, Exception) and name.endswith("Error"):
            if obj is exc.AgentSDKError:
                continue
            assert issubclass(obj, exc.AgentSDKError)

def test_exceptions_can_be_raised_and_caught():
    # Each exception can be raised and caught
    for name in dir(exc):
        obj = getattr(exc, name)
        if isinstance(obj, type) and issubclass(obj, Exception) and name.endswith("Error"):
            if obj is exc.AgentSDKError:
                continue
            with pytest.raises(obj):
                raise obj(f"Test {name}")
