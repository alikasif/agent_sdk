"""Checkpoint manager — serialize/restore step state."""

from __future__ import annotations

import json
import logging
from typing import Any, TYPE_CHECKING

try:
    import msgpack
    _HAS_MSGPACK = True
except ImportError:
    _HAS_MSGPACK = False

from agent_sdk.exceptions import CheckpointError

if TYPE_CHECKING:
    from agent_sdk.core.step import Step
    from agent_sdk.db.repositories.step_repo import StepRepository

logger = logging.getLogger("agent_sdk.durability.checkpoint")


def _serialize(data: dict[str, Any]) -> bytes:
    """Serialize step data to bytes using msgpack (preferred) or JSON fallback."""
    if _HAS_MSGPACK:
        return msgpack.packb(data, use_bin_type=True)
    return json.dumps(data, default=str).encode("utf-8")


def _deserialize(blob: bytes) -> dict[str, Any]:
    """Deserialize bytes back to a dict."""
    if _HAS_MSGPACK:
        try:
            return msgpack.unpackb(blob, raw=False)  # type: ignore[return-value]
        except Exception:
            pass
    return json.loads(blob.decode("utf-8"))


class StepSummary:
    """Lightweight step info returned by list_checkpoints."""

    def __init__(self, step_id: str, session_id: str, step_number: int, status: str) -> None:
        self.id = step_id
        self.session_id = session_id
        self.step_number = step_number
        self.status = status


class CheckpointManager:
    """Serialize and persist step state for durability."""

    def __init__(self, step_repo: StepRepository) -> None:
        self._step_repo = step_repo

    async def save(self, step: Step) -> None:
        """Serialize and persist the step's complete state."""
        try:
            data = step.model_dump(mode="json")
            # Remove checkpoint field to avoid recursive storage
            data.pop("checkpoint", None)
            blob = _serialize(data)
            # Query directly by session_id + step_number
            from agent_sdk.isolation.scope import get_user_scope
            user_id = get_user_scope()
            row = await self._step_repo._db.fetch_one(
                "SELECT id FROM steps WHERE session_id = ? AND step_number = ? AND user_id = ?",
                [step.session_id, step.step_number, user_id],
            )
            if row:
                await self._step_repo.save_checkpoint(row["id"], blob)
                logger.debug("Checkpoint saved for step %d in session %s", step.step_number, step.session_id)
            else:
                logger.warning("No DB row found for step %d in session %s", step.step_number, step.session_id)
        except Exception as exc:
            raise CheckpointError(f"Failed to save checkpoint: {exc}") from exc

    async def load(self, session_id: str, step_number: int) -> Step | None:
        """Restore a step from its checkpoint."""
        try:
            rows = await self._step_repo.get_by_session(session_id)
            for row in rows:
                if row["step_number"] == step_number and row.get("checkpoint"):
                    data = _deserialize(row["checkpoint"])
                    from agent_sdk.core.step import Step
                    return Step.model_validate(data)
            return None
        except Exception as exc:
            raise CheckpointError(f"Failed to load checkpoint: {exc}") from exc

    async def load_latest(self, session_id: str) -> Step | None:
        """Get the last completed checkpoint for a session."""
        try:
            row = await self._step_repo.get_latest_by_session(session_id)
            if row and row.get("checkpoint"):
                data = _deserialize(row["checkpoint"])
                from agent_sdk.core.step import Step
                return Step.model_validate(data)
            return None
        except Exception as exc:
            raise CheckpointError(f"Failed to load latest checkpoint: {exc}") from exc

    async def list_checkpoints(self, session_id: str) -> list[StepSummary]:
        """List step summaries that have checkpoints."""
        rows = await self._step_repo.list_checkpoints(session_id)
        return [
            StepSummary(
                step_id=r["id"],
                session_id=r.get("session_id", session_id),
                step_number=r["step_number"],
                status=r["status"],
            )
            for r in rows
        ]
