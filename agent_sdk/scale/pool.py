"""Semaphore-based concurrency pool for tool execution."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Callable, Awaitable, TypeVar

logger = logging.getLogger("agent_sdk.scale.pool")

T = TypeVar("T")


class ConcurrencyPool:
    """Semaphore-based concurrency limiter for parallel execution."""

    def __init__(self, max_concurrent: int = 10) -> None:
        self._max = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active = 0

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        """Acquire a slot in the pool."""
        await self._semaphore.acquire()
        self._active += 1
        try:
            yield
        finally:
            self._active -= 1
            self._semaphore.release()

    async def run(self, fn: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Execute *fn* within the concurrency pool."""
        async with self.acquire():
            return await fn(*args, **kwargs)

    async def gather(self, tasks: list[Callable[..., Awaitable[Any]]]) -> list[Any]:
        """Execute multiple tasks through the pool concurrently."""

        async def _run_task(task: Callable[..., Awaitable[Any]]) -> Any:
            async with self.acquire():
                return await task()

        return await asyncio.gather(*[_run_task(t) for t in tasks])

    @property
    def active(self) -> int:
        """Number of currently active tasks."""
        return self._active

    @property
    def available(self) -> int:
        """Number of available slots."""
        return self._max - self._active
