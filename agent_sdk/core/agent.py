"""Agent — top-level orchestrator that owns the step-execution loop."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, Callable
from uuid import uuid4

from pydantic import BaseModel, Field

from agent_sdk.config import Settings
from agent_sdk.core.context import RunContext
from agent_sdk.core.llm import LLMAdapter, LiteLLMAdapter
from agent_sdk.core.message import Message, StreamEvent, ToolCall, ToolResult
from agent_sdk.core.session import Session
from agent_sdk.core.step import Step
from agent_sdk.core.tool import Tool, ToolRegistry, tool as tool_decorator
from agent_sdk.db.connection import DatabaseConnection
from agent_sdk.db.repositories.session_repo import SessionRepository
from agent_sdk.db.repositories.step_repo import StepRepository
from agent_sdk.exceptions import (
    SessionNotFoundError,
    StepExecutionError,
    ToolNotFoundError,
)
from agent_sdk.isolation.scope import set_user_scope, clear_user_scope
from agent_sdk.types import (
    ExecutionPolicy,
    MessageRole,
    RunStatus,
    SessionStatus,
    StepStatus,
)

logger = logging.getLogger("agent_sdk.agent")


class AgentResult(BaseModel):
    """Outcome of an Agent.run() invocation."""

    session_id: str
    user_id: str
    messages: list[Message] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    final_output: str = ""
    status: RunStatus = RunStatus.COMPLETED
    resumed_from_step: int | None = None


class Agent:
    """Top-level orchestrator. One Agent instance per agent definition."""

    def __init__(
        self,
        name: str,
        instructions: str | Callable[[RunContext], str],
        tools: list[Tool] | None = None,
        llm: LLMAdapter | None = None,
        settings: Settings | None = None,
        policies: list[Any] | None = None,
    ) -> None:
        self.name = name
        self.instructions = instructions
        self.settings = settings or Settings()
        self.policies = policies or []
        self._registry = ToolRegistry()
        for t in tools or []:
            self._registry.register(t)
        self._llm = llm or LiteLLMAdapter(model=self.settings.default_model)
        self._db: DatabaseConnection | None = None
        self._initialized = False

    # -- Registration helpers ------------------------------------------

    def tool(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        policy: ExecutionPolicy = ExecutionPolicy.AUTO,
    ) -> Callable[[Callable[..., Any]], Tool]:
        """Decorator to register a tool on this agent."""

        def decorator(fn: Callable[..., Any]) -> Tool:
            t = tool_decorator(_fn=fn, name=name, description=description, policy=policy)
            self._registry.register(t)
            return t

        return decorator

    # -- Lifecycle -----------------------------------------------------

    async def initialize(self) -> None:
        """Run DB migrations, warm caches, verify connectivity."""
        if self._initialized:
            return
        self._db = DatabaseConnection(
            db_path=self.settings.db_path,
            pool_size=self.settings.db_pool_size,
        )
        await self._db.initialize()
        self._initialized = True
        logger.info("Agent '%s' initialized.", self.name)

    async def shutdown(self) -> None:
        """Graceful shutdown: close DB connections."""
        if self._db:
            await self._db.close()
        self._initialized = False
        logger.info("Agent '%s' shut down.", self.name)

    # -- Main execution ------------------------------------------------

    async def run(
        self,
        user_id: str,
        input: str | list[Message] | None = None,
        *,
        session_id: str | None = None,
        max_steps: int | None = None,
        resume: bool = False,
    ) -> AgentResult:
        """Execute the agent step loop.

        The run method:
        1. Sets user_scope via ContextVar
        2. Creates or loads a session
        3. Appends user message to history
        4. Loops: build messages → call LLM → execute tools or return output
        5. Returns AgentResult
        """
        await self.initialize()
        assert self._db is not None
        max_steps = max_steps or self.settings.max_steps

        token = set_user_scope(user_id)
        try:
            session_repo = SessionRepository(self._db)
            step_repo = StepRepository(self._db)

            # Create or load session
            resumed_from_step: int | None = None
            if resume and session_id:
                row = await session_repo.get_by_id(session_id)
                if not row:
                    raise SessionNotFoundError(f"Session '{session_id}' not found.")
                session = Session.from_row(row, db=self._db)
                if session.status == SessionStatus.PAUSED:
                    await session.resume()
                # Find last completed step
                latest = await step_repo.get_latest_by_session(session_id)
                if latest:
                    resumed_from_step = latest["step_number"]
            elif session_id:
                row = await session_repo.get_by_id(session_id)
                if not row:
                    raise SessionNotFoundError(f"Session '{session_id}' not found.")
                session = Session.from_row(row, db=self._db)
            else:
                row = await session_repo.create(agent_name=self.name)
                session = Session.from_row(row, db=self._db)

            ctx = RunContext(
                user_id=user_id,
                session=session,
                agent=self,
                db=self._db,
                settings=self.settings,
            )

            # Add user message(s) to history
            if input is not None:
                if isinstance(input, str):
                    msg = Message(role=MessageRole.USER, content=input)
                    await session.add_message(msg)
                else:
                    for m in input:
                        await session.add_message(m)

            # Build the system message
            if callable(self.instructions):
                system_text = self.instructions(ctx)
            else:
                system_text = self.instructions

            # Step loop
            steps: list[Step] = []
            all_messages: list[Message] = []
            tool_schemas = self._registry.to_schemas() if self._registry.list_tools() else None

            for step_num in range(1, max_steps + 1):
                # Build message list from history
                history = await session.get_history(limit=200)
                messages = [Message(role=MessageRole.SYSTEM, content=system_text)] + history

                # Create step record
                step = Step(
                    session_id=session.id,
                    step_number=(resumed_from_step or 0) + step_num,
                )
                step.mark_running()
                step.input_messages = messages

                # Call LLM
                try:
                    llm_response = await self._llm.chat(
                        messages=messages,
                        tools=tool_schemas,
                        temperature=self.settings.default_temperature,
                        max_tokens=self.settings.max_tokens,
                    )
                except Exception as exc:
                    step.mark_failed(str(exc))
                    steps.append(step)
                    return AgentResult(
                        session_id=session.id,
                        user_id=user_id,
                        messages=all_messages,
                        steps=steps,
                        final_output="",
                        status=RunStatus.FAILED,
                        resumed_from_step=resumed_from_step,
                    )

                assistant_msg = llm_response.message
                step.output_message = assistant_msg
                await session.add_message(assistant_msg)
                all_messages.append(assistant_msg)

                # If no tool calls → final output
                if not llm_response.tool_calls:
                    step.mark_completed()
                    steps.append(step)
                    # Persist step
                    await step_repo.create(
                        session_id=session.id,
                        step_number=step.step_number,
                        idempotency_key=step.idempotency_key,
                    )
                    await step_repo.update_status(
                        (await step_repo.get_latest_by_session(session.id))["id"],  # type: ignore[index]
                        status=StepStatus.COMPLETED.value,
                        output_message=assistant_msg.model_dump(mode="json"),
                    )

                    # Mark session completed
                    await session_repo.update_status(session.id, SessionStatus.COMPLETED.value)
                    session.status = SessionStatus.COMPLETED

                    return AgentResult(
                        session_id=session.id,
                        user_id=user_id,
                        messages=all_messages,
                        steps=steps,
                        final_output=assistant_msg.content or "",
                        status=RunStatus.COMPLETED,
                        resumed_from_step=resumed_from_step,
                    )

                # Execute tool calls
                step.tool_calls = llm_response.tool_calls
                tool_results: list[ToolResult] = []

                for tc in llm_response.tool_calls:
                    try:
                        tool_obj = self._registry.get(tc.tool_name)
                    except ToolNotFoundError:
                        tr = ToolResult(
                            tool_call_id=tc.id,
                            error=f"Tool '{tc.tool_name}' not found.",
                        )
                        tool_results.append(tr)
                        continue

                    try:
                        tr = await tool_obj.execute(ctx, **tc.arguments)
                        tr.tool_call_id = tc.id
                        tool_results.append(tr)
                    except Exception as exc:
                        tr = ToolResult(
                            tool_call_id=tc.id,
                            error=str(exc),
                        )
                        tool_results.append(tr)

                step.tool_results = tool_results

                # Add tool results as messages
                for tr in tool_results:
                    tool_msg = Message(
                        role=MessageRole.TOOL,
                        content=json.dumps(tr.output) if tr.output is not None else tr.error,
                        tool_call_id=tr.tool_call_id,
                    )
                    await session.add_message(tool_msg)
                    all_messages.append(tool_msg)

                step.mark_completed()
                steps.append(step)

                # Persist step
                db_step = await step_repo.create(
                    session_id=session.id,
                    step_number=step.step_number,
                    idempotency_key=step.idempotency_key,
                )
                await step_repo.update_status(
                    db_step["id"],
                    status=StepStatus.COMPLETED.value,
                    output_message=assistant_msg.model_dump(mode="json") if assistant_msg else None,
                    tool_calls=[tc.model_dump(mode="json") for tc in step.tool_calls],
                    tool_results=[tr.model_dump(mode="json") for tr in step.tool_results],
                )

            # Max steps reached
            return AgentResult(
                session_id=session.id,
                user_id=user_id,
                messages=all_messages,
                steps=steps,
                final_output="",
                status=RunStatus.FAILED,
                resumed_from_step=resumed_from_step,
            )
        finally:
            clear_user_scope(token)

    async def stream(
        self,
        user_id: str,
        input: str | list[Message],
        *,
        session_id: str | None = None,
        max_steps: int | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream execution events from the agent step loop."""
        await self.initialize()
        assert self._db is not None
        max_steps = max_steps or self.settings.max_steps

        token = set_user_scope(user_id)
        try:
            session_repo = SessionRepository(self._db)

            if session_id:
                row = await session_repo.get_by_id(session_id)
                if not row:
                    raise SessionNotFoundError(f"Session '{session_id}' not found.")
                session = Session.from_row(row, db=self._db)
            else:
                row = await session_repo.create(agent_name=self.name)
                session = Session.from_row(row, db=self._db)

            ctx = RunContext(
                user_id=user_id,
                session=session,
                agent=self,
                db=self._db,
                settings=self.settings,
            )

            # Add user message
            if isinstance(input, str):
                msg = Message(role=MessageRole.USER, content=input)
                await session.add_message(msg)
            else:
                for m in input:
                    await session.add_message(m)

            if callable(self.instructions):
                system_text = self.instructions(ctx)
            else:
                system_text = self.instructions

            tool_schemas = self._registry.to_schemas() if self._registry.list_tools() else None

            for step_num in range(1, max_steps + 1):
                yield StreamEvent(event="step_start", data={"step": step_num})

                history = await session.get_history(limit=200)
                messages = [Message(role=MessageRole.SYSTEM, content=system_text)] + history

                # Use streaming LLM
                collected_content = ""
                collected_tool_calls: list[ToolCall] = []

                async for event in self._llm.chat_stream(
                    messages=messages,
                    tools=tool_schemas,
                    temperature=self.settings.default_temperature,
                    max_tokens=self.settings.max_tokens,
                ):
                    yield event
                    if event.event == "token":
                        collected_content += event.data.get("content", "")
                    elif event.event == "tool_call":
                        # Collect tool calls from stream
                        for tc_data in event.data.get("tool_calls", []):
                            fn_info = tc_data.get("function", {})
                            fn_name = fn_info.get("name", "") if isinstance(fn_info, dict) else getattr(fn_info, "name", "")
                            fn_args_raw = fn_info.get("arguments", "{}") if isinstance(fn_info, dict) else getattr(fn_info, "arguments", "{}")
                            try:
                                fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
                            except (json.JSONDecodeError, TypeError):
                                fn_args = {}
                            call_id = tc_data.get("id", "") if isinstance(tc_data, dict) else getattr(tc_data, "id", "")
                            if fn_name:
                                collected_tool_calls.append(ToolCall(id=call_id, tool_name=fn_name, arguments=fn_args))

                if not collected_tool_calls:
                    # Final output — no tool calls
                    assistant_msg = Message(role=MessageRole.ASSISTANT, content=collected_content)
                    await session.add_message(assistant_msg)
                    yield StreamEvent(event="step_end", data={"step": step_num})
                    yield StreamEvent(event="done", data={"output": collected_content})
                    return

                # Execute collected tool calls
                assistant_msg = Message(
                    role=MessageRole.ASSISTANT,
                    content=collected_content or None,
                    tool_calls=collected_tool_calls,
                )
                await session.add_message(assistant_msg)

                for tc in collected_tool_calls:
                    try:
                        tool_obj = self._registry.get(tc.tool_name)
                        tr = await tool_obj.execute(ctx, **tc.arguments)
                        tr.tool_call_id = tc.id
                    except Exception as exc:
                        tr = ToolResult(tool_call_id=tc.id, error=str(exc))

                    tool_msg = Message(
                        role=MessageRole.TOOL,
                        content=json.dumps(tr.output) if tr.output is not None else tr.error,
                        tool_call_id=tr.tool_call_id,
                    )
                    await session.add_message(tool_msg)
                    yield StreamEvent(event="tool_result", data={"tool_call_id": tr.tool_call_id, "output": tr.output, "error": tr.error})

                yield StreamEvent(event="step_end", data={"step": step_num})

            yield StreamEvent(event="done", data={"output": "", "reason": "max_steps_reached"})
        finally:
            clear_user_scope(token)
