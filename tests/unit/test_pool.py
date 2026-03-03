"""Unit tests for agent_sdk.scale.pool.ConcurrencyPool."""
import pytest
import asyncio
from agent_sdk.scale.pool import ConcurrencyPool

@pytest.mark.asyncio
async def test_concurrency_pool_acquire_release():
    pool = ConcurrencyPool(max_concurrent=2)
    async with pool.acquire():
        assert pool.active == 1
        assert pool.available == 1
    assert pool.active == 0
    assert pool.available == 2

@pytest.mark.asyncio
async def test_concurrency_pool_run():
    pool = ConcurrencyPool(max_concurrent=1)
    async def fn():
        await asyncio.sleep(0.01)
        return "done"
    result = await pool.run(fn)
    assert result == "done"

@pytest.mark.asyncio
async def test_concurrency_pool_gather_limits_concurrency():
    pool = ConcurrencyPool(max_concurrent=2)
    started = []
    async def task(i):
        started.append(i)
        await asyncio.sleep(0.01)
        return i
    tasks = [lambda i=i: task(i) for i in range(4)]
    results = await pool.gather(tasks)
    assert sorted(results) == [0, 1, 2, 3]
    # At least two tasks should have started before any finished
    assert len(started) >= 2
