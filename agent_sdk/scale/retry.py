"""Configurable retry with exponential backoff + jitter."""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from typing import Any, Callable, Awaitable, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger("agent_sdk.scale.retry")

T = TypeVar("T")


class RetryPolicy(BaseModel):
    """Configuration for retry behaviour."""

    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)

    model_config = {"arbitrary_types_allowed": True}


async def with_retry(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    policy: RetryPolicy | None = None,
    **kwargs: Any,
) -> T:
    """Execute *fn* with retries according to *policy*."""
    pol = policy or RetryPolicy()
    last_exc: Exception | None = None

    for attempt in range(pol.max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except pol.retryable_exceptions as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt == pol.max_retries:
                break
            delay = min(pol.base_delay * (pol.exponential_base ** attempt), pol.max_delay)
            if pol.jitter:
                delay *= random.uniform(0.5, 1.5)
            logger.warning(
                "Retry %d/%d for %s after %.2fs: %s",
                attempt + 1,
                pol.max_retries,
                fn.__name__ if hasattr(fn, "__name__") else str(fn),
                delay,
                exc,
            )
            await asyncio.sleep(delay)

    raise last_exc  # type: ignore[misc]


def retry(policy: RetryPolicy | None = None) -> Callable:
    """Decorator form of with_retry."""

    def decorator(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await with_retry(fn, *args, policy=policy, **kwargs)

        return wrapper

    return decorator
