"""Unit tests for agent_sdk.scale.circuit_breaker.CircuitBreaker."""
import pytest
import asyncio
from agent_sdk.scale.circuit_breaker import CircuitBreaker
from agent_sdk.types import CircuitState
from agent_sdk.exceptions import CircuitOpenError

@pytest.mark.asyncio
async def test_circuit_breaker_state_transitions():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    assert cb.state == CircuitState.CLOSED

    async def fail():
        raise Exception("fail")

    # Failures to open
    for _ in range(2):
        with pytest.raises(Exception):
            await cb.call(fail)
    assert cb.state == CircuitState.OPEN

    # Should transition to HALF_OPEN after recovery_timeout
    await asyncio.sleep(0.11)
    assert cb.state == CircuitState.HALF_OPEN

    # Success in half-open closes circuit
    async def succeed():
        return "ok"
    result = await cb.call(succeed)
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED

    # Fail again to open
    for _ in range(2):
        with pytest.raises(Exception):
            await cb.call(fail)
    assert cb.state == CircuitState.OPEN

    # Half-open, fail again
    await asyncio.sleep(0.11)
    assert cb.state == CircuitState.HALF_OPEN
    with pytest.raises(Exception):
        await cb.call(fail)
    assert cb.state == CircuitState.OPEN

@pytest.mark.asyncio
async def test_circuit_breaker_open_rejects():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
    async def fail():
        raise Exception("fail")
    with pytest.raises(Exception):
        await cb.call(fail)
    assert cb.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        await cb.call(lambda: "should not run")
