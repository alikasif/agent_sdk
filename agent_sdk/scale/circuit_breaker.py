"""Circuit breaker for external API calls."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Awaitable, TypeVar

from agent_sdk.exceptions import CircuitOpenError
from agent_sdk.types import CircuitState

logger = logging.getLogger("agent_sdk.scale.circuit_breaker")

T = TypeVar("T")


class CircuitBreaker:
    """Circuit breaker pattern: closed → open → half_open → closed."""

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        """Current circuit state, with automatic transition from OPEN to HALF_OPEN."""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit '%s' transitioned to HALF_OPEN", self.name)
        return self._state

    async def call(self, fn: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Execute *fn* through the circuit breaker."""
        current = self.state

        if current == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit '{self.name}' is OPEN; call rejected.")

        if current == CircuitState.HALF_OPEN and self._half_open_calls >= self.half_open_max:
            raise CircuitOpenError(f"Circuit '{self.name}' is HALF_OPEN with max probes reached.")

        if current == CircuitState.HALF_OPEN:
            self._half_open_calls += 1

        try:
            result = await fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure()
            raise

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            # Transition back to CLOSED
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            logger.info("Circuit '%s' transitioned to CLOSED", self.name)
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning("Circuit '%s' transitioned back to OPEN from HALF_OPEN", self.name)
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit '%s' transitioned to OPEN after %d failures",
                self.name,
                self._failure_count,
            )

    def reset(self) -> None:
        """Forcefully reset the circuit to CLOSED."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        logger.info("Circuit '%s' manually reset to CLOSED", self.name)
