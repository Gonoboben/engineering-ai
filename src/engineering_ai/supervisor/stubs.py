"""Fake/stub execution helpers used before real tool adapters exist."""

from __future__ import annotations

from dataclasses import dataclass, field

from engineering_ai.supervisor.core import ToolOutcome


@dataclass
class StubTool:
    """Deterministic callable tool for Supervisor tests and development."""

    outcome: ToolOutcome
    calls: list[str] = field(default_factory=list)

    def __call__(self, action: str) -> ToolOutcome:
        self.calls.append(action)
        return self.outcome
