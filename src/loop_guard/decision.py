"""Decision types and action configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Action(Enum):
    """What to do when a loop pattern is detected."""

    CONTINUE = auto()
    WARN = auto()
    STOP = auto()
    ESCALATE = auto()


@dataclass(frozen=True, slots=True)
class Decision:
    """Result of a loop guard check."""

    action: Action
    reason: str = ""
    strategy: str = ""  # which strategy triggered
    confidence: float = 0.0  # 0.0 ~ 1.0
    step_number: int = 0

    @property
    def is_loop(self) -> bool:
        return self.action in (Action.STOP, Action.ESCALATE)

    @property
    def should_warn(self) -> bool:
        return self.action == Action.WARN


@dataclass
class ActionConfig:
    """Configure how many warnings before escalation."""

    warn_threshold: int = 2
    stop_threshold: int = 4
    escalate_threshold: int = 6
    reflection_message: str = "You appear to be stuck in a loop. Try a different approach."

    def resolve_action(self, consecutive_hits: int) -> Action:
        """Map hit count to action."""
        if consecutive_hits >= self.escalate_threshold:
            return Action.ESCALATE
        if consecutive_hits >= self.stop_threshold:
            return Action.STOP
        if consecutive_hits >= self.warn_threshold:
            return Action.WARN
        return Action.CONTINUE
