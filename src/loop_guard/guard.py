"""Core LoopGuard — orchestrates detection strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loop_guard.decision import ActionConfig, Decision
from loop_guard.strategies import (
    ActionRecord,
    CycleDetectionStrategy,
    ExactRepeatStrategy,
    FuzzyRepeatStrategy,
    OutputStagnationStrategy,
)


@dataclass
class LoopGuard:
    """Framework-agnostic agent loop detector.

    Usage:
        guard = LoopGuard()

        for action in agent_actions:
            decision = guard.check(action.tool, action.args, action.output)
            if decision.action == Action.STOP:
                break
            if decision.should_warn:
                print(f"Warning: {decision.reason}")
    """

    window_size: int = 10
    similarity_threshold: float = 0.85
    action_config: ActionConfig = field(default_factory=ActionConfig)

    # Strategy instances (auto-created)
    _exact: ExactRepeatStrategy = field(init=False, repr=False)
    _fuzzy: FuzzyRepeatStrategy = field(init=False, repr=False)
    _cycle: CycleDetectionStrategy = field(init=False, repr=False)
    _stagnation: OutputStagnationStrategy = field(init=False, repr=False)

    # State
    _step: int = field(default=0, init=False, repr=False)
    _consecutive_hits: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._exact = ExactRepeatStrategy(window_size=self.window_size)
        self._fuzzy = FuzzyRepeatStrategy(
            window_size=self.window_size,
            similarity_threshold=self.similarity_threshold,
        )
        self._cycle = CycleDetectionStrategy(max_cycle_length=min(self.window_size, 5))
        self._stagnation = OutputStagnationStrategy(
            window_size=self.window_size,
            similarity_threshold=self.similarity_threshold,
        )

    def check(
        self,
        tool: str,
        args: dict[str, Any] | str | None = None,
        output: str | None = None,
    ) -> Decision:
        """Check an agent action for loop patterns.

        Args:
            tool: Name of the tool/function being called.
            args: Arguments passed to the tool.
            output: Output/result of the tool call (optional, enables stagnation detection).

        Returns:
            Decision with action (CONTINUE/WARN/STOP/ESCALATE), reason, and confidence.
        """
        self._step += 1
        record = ActionRecord(tool=tool, args=args, output=output, step=self._step)

        # Run all strategies and take the highest confidence
        results = [
            ("exact_repeat", *self._exact.check(record)),
            ("fuzzy_repeat", *self._fuzzy.check(record)),
            ("cycle_detection", *self._cycle.check(record)),
            ("output_stagnation", *self._stagnation.check(record)),
        ]

        # Find highest confidence detection
        best_strategy = ""
        best_confidence = 0.0
        best_reason = ""

        for strategy_name, confidence, reason in results:
            if confidence > best_confidence:
                best_strategy = strategy_name
                best_confidence = confidence
                best_reason = reason

        # Update consecutive hit counter
        if best_confidence > 0.3:
            self._consecutive_hits += 1
        else:
            self._consecutive_hits = 0

        # Determine action based on consecutive hits
        action = self.action_config.resolve_action(self._consecutive_hits)

        return Decision(
            action=action,
            reason=best_reason,
            strategy=best_strategy,
            confidence=best_confidence,
            step_number=self._step,
        )

    def reset(self) -> None:
        """Reset all state for reuse."""
        self._step = 0
        self._consecutive_hits = 0
        self._exact.reset()
        self._fuzzy.reset()
        self._cycle.reset()
        self._stagnation.reset()

    @property
    def step_count(self) -> int:
        return self._step

    @property
    def consecutive_hits(self) -> int:
        return self._consecutive_hits
