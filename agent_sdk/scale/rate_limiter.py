"""Rate limiter — configure litellm’s built-in rate limiting."""

from __future__ import annotations

import logging

logger = logging.getLogger("agent_sdk.scale.rate_limiter")


def configure_rate_limits(
    model: str,
    rpm: int | None = None,
    tpm: int | None = None,
) -> None:
    """Configure litellm rate limits for a specific model.

    Parameters
    ----------
    model:
        The model name (e.g., 'gpt-4').
    rpm:
        Requests per minute limit.
    tpm:
        Tokens per minute limit.
    """
    try:
        import litellm

        if rpm is not None:
            litellm.rpm_limit = rpm  # type: ignore[attr-defined]
            logger.info("Rate limit set: %s RPM=%d", model, rpm)
        if tpm is not None:
            litellm.tpm_limit = tpm  # type: ignore[attr-defined]
            logger.info("Rate limit set: %s TPM=%d", model, tpm)
    except ImportError:
        logger.warning("litellm not installed; rate limiting not configured.")


class RateLimiter:
    """Token-bucket rate limiter (per model provider).

    This is a simple async token-bucket implementation for when
    litellm's built-in limits are insufficient.
    """

    def __init__(self, rate: float, burst: int, name: str = "default") -> None:
        self.rate = rate  # tokens per second
        self.burst = burst
        self.name = name
        self._tokens = float(burst)
        self._last_refill = 0.0

    def _refill(self) -> None:
        import time
        now = time.monotonic()
        if self._last_refill == 0.0:
            self._last_refill = now
            return
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now

    async def acquire(self, tokens: int = 1) -> None:
        """Block until tokens are available."""
        import asyncio
        while True:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return
            # Wait for enough tokens to accumulate
            wait_time = (tokens - self._tokens) / self.rate
            await asyncio.sleep(wait_time)

    def try_acquire(self, tokens: int = 1) -> bool:
        """Non-blocking check."""
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens."""
        self._refill()
        return self._tokens
