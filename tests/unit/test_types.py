"""Unit tests for agent_sdk.types enums."""
import pytest
from agent_sdk.types import (
    StepStatus, SessionStatus, RunStatus, MessageRole,
    ExecutionPolicy, ApprovalStatus, MemoryType, CircuitState
)

def test_step_status_enum():
    assert StepStatus.PENDING == "pending"
    assert StepStatus.RUNNING == "running"
    assert StepStatus.COMPLETED == "completed"
    assert StepStatus.FAILED == "failed"
    assert StepStatus.SKIPPED == "skipped"
    assert set(StepStatus) == {
        StepStatus.PENDING, StepStatus.RUNNING, StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED
    }

def test_session_status_enum():
    assert SessionStatus.ACTIVE == "active"
    assert SessionStatus.PAUSED == "paused"
    assert SessionStatus.COMPLETED == "completed"
    assert SessionStatus.ARCHIVED == "archived"
    assert set(SessionStatus) == {
        SessionStatus.ACTIVE, SessionStatus.PAUSED, SessionStatus.COMPLETED, SessionStatus.ARCHIVED
    }

def test_run_status_enum():
    assert RunStatus.COMPLETED == "completed"
    assert RunStatus.PAUSED == "paused"
    assert RunStatus.FAILED == "failed"
    assert set(RunStatus) == {
        RunStatus.COMPLETED, RunStatus.PAUSED, RunStatus.FAILED
    }

def test_message_role_enum():
    assert MessageRole.USER == "user"
    assert MessageRole.ASSISTANT == "assistant"
    assert MessageRole.SYSTEM == "system"
    assert MessageRole.TOOL == "tool"
    assert set(MessageRole) == {
        MessageRole.USER, MessageRole.ASSISTANT, MessageRole.SYSTEM, MessageRole.TOOL
    }

def test_execution_policy_enum():
    assert ExecutionPolicy.AUTO == "auto"
    assert ExecutionPolicy.HUMAN_APPROVAL == "human_approval"
    assert ExecutionPolicy.ADMIN_SIGNOFF == "admin_signoff"
    assert set(ExecutionPolicy) == {
        ExecutionPolicy.AUTO, ExecutionPolicy.HUMAN_APPROVAL, ExecutionPolicy.ADMIN_SIGNOFF
    }

def test_approval_status_enum():
    assert ApprovalStatus.PENDING == "pending"
    assert ApprovalStatus.APPROVED == "approved"
    assert ApprovalStatus.DENIED == "denied"
    assert ApprovalStatus.EXPIRED == "expired"
    assert set(ApprovalStatus) == {
        ApprovalStatus.PENDING, ApprovalStatus.APPROVED, ApprovalStatus.DENIED, ApprovalStatus.EXPIRED
    }

def test_memory_type_enum():
    assert MemoryType.SHORT_TERM == "short_term"
    assert MemoryType.LONG_TERM == "long_term"
    assert set(MemoryType) == {MemoryType.SHORT_TERM, MemoryType.LONG_TERM}

def test_circuit_state_enum():
    assert CircuitState.CLOSED == "closed"
    assert CircuitState.OPEN == "open"
    assert CircuitState.HALF_OPEN == "half_open"
    assert set(CircuitState) == {
        CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN
    }
