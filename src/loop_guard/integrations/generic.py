"""Generic callback adapter for any agent framework."""

from __future__ import annotations

from typing import Any, Callable

from loop_guard.decision import Action, Decision
from loop_guard.guard import LoopGuard


class LoopGuardCallback:
    """Wrap LoopGuard as a callback for any agent framework.

    Usage:
        callback = LoopGuardCallback(
            on_warn=lambda d: print(f"Warning: {d.reason}"),
            on_stop=lambda d: raise StopIteration(),
        )

        # In your agent loop:
        decision = callback.before_tool_call("search", {"query": "test"})
    """

    def __init__(
        self,
        guard: LoopGuard | None = None,
        on_warn: Callable[[Decision], None] | None = None,
        on_stop: Callable[[Decision], Any] | None = None,
        on_escalate: Callable[[Decision], Any] | None = None,
        **guard_kwargs: Any,
    ):
        self.guard = guard or LoopGuard(**guard_kwargs)
        self._on_warn = on_warn
        self._on_stop = on_stop
        self._on_escalate = on_escalate

    def before_tool_call(
        self,
        tool: str,
        args: dict | str | None = None,
        output: str | None = None,
    ) -> Decision:
        """Check and dispatch callbacks. Returns the Decision."""
        decision = self.guard.check(tool, args, output)

        if decision.action == Action.WARN and self._on_warn:
            self._on_warn(decision)
        elif decision.action == Action.STOP and self._on_stop:
            self._on_stop(decision)
        elif decision.action == Action.ESCALATE and self._on_escalate:
            self._on_escalate(decision)

        return decision

    def reset(self) -> None:
        self.guard.reset()
