"""Unit tests for agent_sdk.scale.retry: with_retry and @retry."""
import pytest
import asyncio
from agent_sdk.scale.retry import with_retry, RetryPolicy

@pytest.mark.asyncio
async def test_with_retry_succeeds_first_try():
    async def fn():
        return 42
    result = await with_retry(fn)
    assert result == 42

@pytest.mark.asyncio
async def test_with_retry_retries_and_succeeds():
    attempts = []
    async def fn():
        attempts.append(1)
        if len(attempts) < 3:
            raise Exception("fail")
        return "ok"
    result = await with_retry(fn, policy=RetryPolicy(max_retries=5, base_delay=0.01, max_delay=0.05))
    assert result == "ok"
    assert len(attempts) == 3

@pytest.mark.asyncio
async def test_with_retry_respects_max_retries():
    async def fn():
        raise Exception("fail")
    with pytest.raises(Exception):
        await with_retry(fn, policy=RetryPolicy(max_retries=2, base_delay=0.01, max_delay=0.05))

@pytest.mark.asyncio
async def test_with_retry_exponential_backoff(monkeypatch):
    delays = []
    async def fn():
        raise Exception("fail")
    async def sleep_patch(delay):
        delays.append(delay)
    monkeypatch.setattr(asyncio, "sleep", sleep_patch)
    with pytest.raises(Exception):
        await with_retry(fn, policy=RetryPolicy(max_retries=3, base_delay=1, max_delay=10, exponential_base=2, jitter=False))
    # Should see exponential delays: 1, 2, 4
    assert delays[:3] == [1.0, 2.0, 4.0]
