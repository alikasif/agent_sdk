"""Async request queue with priority + backpressure."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from agent_sdk.exceptions import BackpressureError

logger = logging.getLogger("agent_sdk.scale.queue")


@dataclass(order=True)
class _QueueEntry:
    """Internal priority queue entry."""

    priority: int
    request_id: str = field(compare=False)
    request: Any = field(compare=False)
    future: asyncio.Future = field(compare=False, repr=False)


class RequestQueue:
    """Async request queue with priority ordering and backpressure."""

    def __init__(self, max_size: int = 1000, max_workers: int = 10) -> None:
        self._max_size = max_size
        self._max_workers = max_workers
        self._queue: asyncio.PriorityQueue[_QueueEntry] = asyncio.PriorityQueue(maxsize=max_size)
        self._results: dict[str, asyncio.Future] = {}
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._handler: Any = None
        self._active_count = 0

    def set_handler(self, handler: Any) -> None:
        """Set the handler function that processes requests."""
        self._handler = handler

    async def submit(self, request: Any, priority: int = 0) -> str:
        """Submit a request. Returns a request_id. Raises BackpressureError if full."""
        if self._queue.qsize() >= self._max_size:
            raise BackpressureError("Request queue is full; apply backpressure.")

        request_id = uuid4().hex
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._results[request_id] = future

        entry = _QueueEntry(
            priority=priority,
            request_id=request_id,
            request=request,
            future=future,
        )
        await self._queue.put(entry)
        logger.debug("Request %s submitted with priority %d", request_id, priority)
        return request_id

    async def get_result(self, request_id: str, timeout: float = 300.0) -> Any:
        """Wait for and return the result of a request."""
        future = self._results.get(request_id)
        if future is None:
            raise KeyError(f"Request '{request_id}' not found.")
        return await asyncio.wait_for(future, timeout=timeout)

    async def cancel(self, request_id: str) -> None:
        """Cancel a pending request."""
        future = self._results.pop(request_id, None)
        if future and not future.done():
            future.cancel()

    async def start(self) -> None:
        """Start worker tasks."""
        if self._running:
            return
        self._running = True
        for i in range(self._max_workers):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)
        logger.info("Request queue started with %d workers", self._max_workers)

    async def stop(self) -> None:
        """Stop all workers and drain the queue."""
        self._running = False
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("Request queue stopped.")

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes queue entries."""
        while self._running:
            try:
                entry = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            self._active_count += 1
            try:
                if self._handler:
                    result = await self._handler(entry.request)
                    if not entry.future.done():
                        entry.future.set_result(result)
                else:
                    if not entry.future.done():
                        entry.future.set_result(None)
            except Exception as exc:
                if not entry.future.done():
                    entry.future.set_exception(exc)
            finally:
                self._active_count -= 1
                self._queue.task_done()

    @property
    def pending_count(self) -> int:
        """Number of pending items in the queue."""
        return self._queue.qsize()

    @property
    def active_count(self) -> int:
        """Number of currently processing items."""
        return self._active_count
