"""Rule engine — evaluates tool + context → required authority level."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from agent_sdk.governance.policy import PolicyRule
from agent_sdk.types import ExecutionPolicy

if TYPE_CHECKING:
    from agent_sdk.core.context import RunContext
    from agent_sdk.core.tool import Tool

# Priority ordering: higher value = stricter policy
_POLICY_PRIORITY = {
    ExecutionPolicy.AUTO: 0,
    ExecutionPolicy.HUMAN_APPROVAL: 1,
    ExecutionPolicy.ADMIN_SIGNOFF: 2,
}


class RuleEngine:
    """Evaluate policy rules to determine the required authority level."""

    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self._rules = rules or []

    def evaluate(self, tool: Tool, ctx: Any = None) -> ExecutionPolicy:
        """Return the highest required authority level for this tool+context.

        Matching logic:
        1. Collect all rules where tool_name matches or is None (wildcard).
        2. Also consider the tool's own policy attribute.
        3. Return the policy with the highest priority.
        """
        candidates: list[ExecutionPolicy] = []

        # Tool's own declared policy
        if hasattr(tool, 'policy'):
            candidates.append(tool.policy)

        # Matching rules
        for rule in self._rules:
            if rule.tool_name is None or rule.tool_name == tool.name:
                candidates.append(rule.policy)

        if not candidates:
            return ExecutionPolicy.AUTO

        # Return the strictest (highest priority)
        return max(candidates, key=lambda p: _POLICY_PRIORITY.get(p, 0))
