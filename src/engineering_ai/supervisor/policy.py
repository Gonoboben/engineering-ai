"""Deterministic policy decisions for the Engineering AI Supervisor."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from engineering_ai.validation import SemanticValidationError, validate_instance


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    NEEDS_HUMAN_APPROVAL = "NEEDS_HUMAN_APPROVAL"


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    decision: Decision
    reason: str
    approval_required: bool = False
    approval_obtained: bool = False
    approver: str | None = None


class PolicyEngine:
    """Evaluate actions against validated project policy and effective state."""

    def __init__(self, policy: dict[str, Any], state: dict[str, Any]) -> None:
        validate_instance("project-policy.schema.json", policy)
        validate_instance("project-state.schema.json", state)
        if policy["project_id"] != state["project_id"]:
            raise SemanticValidationError("policy/state project_id mismatch")
        self._policy = policy
        self._state = state
        self._validate_state_is_not_weaker_than_policy()

    def evaluate(
        self,
        action: str,
        *,
        approval_obtained: bool = False,
        approver: str | None = None,
    ) -> PolicyDecision:
        permissions = self._state["effective_permissions"]

        if action in permissions["forbidden"]:
            return PolicyDecision(
                action=action,
                decision=Decision.DENY,
                reason="action is forbidden by effective project state",
            )

        if action in permissions["approval_required"]:
            if not approval_obtained:
                return PolicyDecision(
                    action=action,
                    decision=Decision.NEEDS_HUMAN_APPROVAL,
                    reason="action requires explicit human approval",
                    approval_required=True,
                )
            if not approver:
                return PolicyDecision(
                    action=action,
                    decision=Decision.NEEDS_HUMAN_APPROVAL,
                    reason="approval was asserted without an approver identity",
                    approval_required=True,
                )
            return PolicyDecision(
                action=action,
                decision=Decision.ALLOW,
                reason="explicit human approval satisfies the effective policy boundary",
                approval_required=True,
                approval_obtained=True,
                approver=approver,
            )

        if action in permissions["autonomous"]:
            return PolicyDecision(
                action=action,
                decision=Decision.ALLOW,
                reason="action is autonomous in effective project state",
            )

        return PolicyDecision(
            action=action,
            decision=Decision.DENY,
            reason="action is not present in effective project permissions",
        )

    def _validate_state_is_not_weaker_than_policy(self) -> None:
        effective = self._state["effective_permissions"]
        policy_autonomous = set(self._policy["autonomous_actions"])
        policy_approval = set(self._policy["approval_required_actions"])
        policy_forbidden = set(self._policy["forbidden_actions"])

        effective_autonomous = set(effective["autonomous"])
        effective_approval = set(effective["approval_required"])

        relaxed_to_autonomous = effective_autonomous - policy_autonomous
        if relaxed_to_autonomous:
            raise SemanticValidationError(
                "effective state cannot grant autonomous authority beyond project policy: "
                f"{sorted(relaxed_to_autonomous)}"
            )

        forbidden_relaxed = policy_forbidden & (effective_autonomous | effective_approval)
        if forbidden_relaxed:
            raise SemanticValidationError(
                "effective state cannot relax policy-forbidden actions: "
                f"{sorted(forbidden_relaxed)}"
            )

        approval_relaxed = policy_approval & effective_autonomous
        if approval_relaxed:
            raise SemanticValidationError(
                "effective state cannot relax approval-required actions to autonomous: "
                f"{sorted(approval_relaxed)}"
            )
