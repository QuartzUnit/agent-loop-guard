"""Tests for integration adapters."""

from loop_guard import Action, LoopGuard
from loop_guard.integrations.generic import LoopGuardCallback


class TestGenericCallback:
    def test_callback_dispatches_on_warn(self):
        warnings = []
        callback = LoopGuardCallback(
            window_size=3,
            on_warn=lambda d: warnings.append(d),
        )

        # Trigger warnings via exact repeat
        for _ in range(6):
            callback.before_tool_call("search", {"q": "test"})

        assert len(warnings) > 0

    def test_callback_dispatches_on_stop(self):
        stops = []
        callback = LoopGuardCallback(
            window_size=3,
            on_stop=lambda d: stops.append(d),
        )

        for _ in range(10):
            callback.before_tool_call("search", {"q": "test"})

        assert len(stops) > 0

    def test_callback_no_dispatch_on_normal(self):
        warnings = []
        stops = []
        callback = LoopGuardCallback(
            on_warn=lambda d: warnings.append(d),
            on_stop=lambda d: stops.append(d),
        )

        callback.before_tool_call("search", {"q": "alpha"})
        callback.before_tool_call("read", {"path": "file.py"})
        callback.before_tool_call("edit", {"path": "file.py"})

        assert len(warnings) == 0
        assert len(stops) == 0

    def test_callback_returns_decision(self):
        callback = LoopGuardCallback()
        decision = callback.before_tool_call("test", {})
        assert decision.action == Action.CONTINUE

    def test_callback_reset(self):
        callback = LoopGuardCallback()
        for _ in range(5):
            callback.before_tool_call("search", {"q": "test"})
        callback.reset()
        d = callback.before_tool_call("search", {"q": "test"})
        assert d.action == Action.CONTINUE

    def test_callback_accepts_guard_instance(self):
        guard = LoopGuard(window_size=5)
        callback = LoopGuardCallback(guard=guard)
        assert callback.guard is guard

    def test_callback_passes_output(self):
        callback = LoopGuardCallback(window_size=3)
        d = callback.before_tool_call("test", {}, output="FAIL")
        assert isinstance(d.action, Action)
