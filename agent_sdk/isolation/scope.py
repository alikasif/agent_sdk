"""ContextVar-based user scope for isolation enforcement."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from contextvars import ContextVar, Token

from agent_sdk.exceptions import IsolationViolationError

_current_user_id: ContextVar[str] = ContextVar("_current_user_id")


def set_user_scope(user_id: str) -> Token[str]:
    """Bind *user_id* to the current async context."""
    return _current_user_id.set(user_id)


def get_user_scope() -> str:
    """Return the current user_id or raise."""
    try:
        return _current_user_id.get()
    except LookupError:
        raise IsolationViolationError("User scope is not set; call set_user_scope() first.")


def clear_user_scope(token: Token[str]) -> None:
    """Reset user scope to its previous value."""
    _current_user_id.reset(token)


@contextlib.asynccontextmanager
async def user_scope(user_id: str) -> AsyncIterator[None]:
    """Async context manager that sets and clears user scope."""
    token = set_user_scope(user_id)
    try:
        yield
    finally:
        clear_user_scope(token)
