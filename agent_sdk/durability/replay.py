"""Replay engine — replay completed steps from checkpoints without re-execution."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agent_sdk.exceptions import ReplayError

if TYPE_CHECKING:
    from agent_sdk.core.message import Message
    from agent_sdk.core.step import Step
    from agent_sdk.durability.checkpoint import CheckpointManager
    from agent_sdk.durability.idempotency import IdempotencyTracker

logger = logging.getLogger("agent_sdk.durability.replay")


class ResumePoint(BaseModel):
    """Information needed to resume from a checkpoint."""

    session_id: str
    resume_step: int
    replayed_steps: list[dict] = Field(default_factory=list)
    pending_messages: list[dict] = Field(default_factory=list)


class ReplayEngine:
    """Replays completed steps from checkpoints without re-executing side effects."""

    def __init__(
        self,
        checkpoint_mgr: CheckpointManager,
        idempotency: IdempotencyTracker,
    ) -> None:
        self._checkpoint = checkpoint_mgr
        self._idempotency = idempotency

    async def replay_to(self, session_id: str, step_number: int) -> list[Step]:
        """Replay steps 1..N from checkpoints (no re-execution)."""
        try:
            replayed: list[Step] = []
            for sn in range(1, step_number + 1):
                step = await self._checkpoint.load(session_id, sn)
                if step:
                    replayed.append(step)
                else:
                    logger.warning("Checkpoint missing for step %d in session %s", sn, session_id)
            return replayed
        except Exception as exc:
            raise ReplayError(f"Failed to replay to step {step_number}: {exc}") from exc

    async def resume_from(self, session_id: str) -> ResumePoint:
        """Find the last clean checkpoint and prepare for resumption."""
        try:
            latest = await self._checkpoint.load_latest(session_id)
            if latest is None:
                return ResumePoint(
                    session_id=session_id,
                    resume_step=1,
                )

            replayed = await self.replay_to(session_id, latest.step_number)
            # Collect messages from replayed steps for context rebuild
            pending_messages: list[dict] = []
            for step in replayed:
                if step.output_message:
                    pending_messages.append(step.output_message.model_dump(mode="json"))
                for tr in step.tool_results:
                    pending_messages.append({
                        "role": "tool",
                        "content": str(tr.output),
                        "tool_call_id": tr.tool_call_id,
                    })

            return ResumePoint(
                session_id=session_id,
                resume_step=latest.step_number + 1,
                replayed_steps=[s.model_dump(mode="json") for s in replayed],
                pending_messages=pending_messages,
            )
        except Exception as exc:
            raise ReplayError(f"Failed to prepare resume point: {exc}") from exc
