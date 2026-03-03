"""Runtime assertions that records belong to the expected user."""

from __future__ import annotations

from typing import Any

from agent_sdk.exceptions import IsolationViolationError


class IsolationValidator:
    """Post-hoc validation — the third isolation layer."""

    @staticmethod
    def assert_owns(record: dict[str, Any], expected_user_id: str) -> None:
        """Raise if *record* doesn't belong to *expected_user_id*."""
        actual = record.get("user_id")
        if actual != expected_user_id:
            raise IsolationViolationError(
                f"Record belongs to user '{actual}', expected '{expected_user_id}'."
            )

    @staticmethod
    def assert_all_owned(records: list[dict[str, Any]], expected_user_id: str) -> None:
        """Raise if any record in *records* fails ownership check."""
        for record in records:
            IsolationValidator.assert_owns(record, expected_user_id)
