"""Tests for LoopGuard core."""

from loop_guard import Action, ActionConfig, Decision, LoopGuard
from tests.fixtures.scenarios import (
    CYCLE_SCENARIO,
    EXACT_REPEAT_SCENARIO,
    FUZZY_REPEAT_SCENARIO,
    LONG_NORMAL_SCENARIO,
    NORMAL_SCENARIO,
    STAGNATION_SCENARIO,
)


class TestLoopGuardDetection:
    """Test detection of various loop patterns."""

    def test_detects_exact_repeat(self):
        guard = LoopGuard(window_size=5)
        results = []
        for tool, args in EXACT_REPEAT_SCENARIO:
            d = guard.check(tool, args)
            results.append(d)

        # Should detect loop by the end
        assert any(d.action in (Action.WARN, Action.STOP, Action.ESCALATE) for d in results)
        assert any(d.confidence > 0 for d in results)

    def test_detects_fuzzy_repeat(self):
        guard = LoopGuard(window_size=5, similarity_threshold=0.7)
        results = []
        for tool, args in FUZZY_REPEAT_SCENARIO:
            d = guard.check(tool, args)
            results.append(d)

        # Should detect similarity
        assert any(d.confidence > 0 for d in results)

    def test_detects_cycle(self):
        guard = LoopGuard(window_size=10)
        results = []
        for tool, args in CYCLE_SCENARIO:
            d = guard.check(tool, args)
            results.append(d)

        # Should detect the A→B→C cycle
        cycle_detections = [d for d in results if d.strategy == "cycle_detection" and d.confidence > 0]
        assert len(cycle_detections) > 0

    def test_detects_stagnation(self):
        guard = LoopGuard(window_size=5)
        results = []
        for tool, args, output in STAGNATION_SCENARIO:
            d = guard.check(tool, args, output)
            results.append(d)

        stag = [d for d in results if d.confidence > 0]
        assert len(stag) > 0

    def test_normal_scenario_passes(self):
        guard = LoopGuard(window_size=5)
        for tool, args in NORMAL_SCENARIO:
            d = guard.check(tool, args)
            assert d.action != Action.STOP
            assert d.action != Action.ESCALATE

    def test_long_normal_no_false_positive(self):
        guard = LoopGuard(window_size=10)
        for tool, args in LONG_NORMAL_SCENARIO:
            d = guard.check(tool, args)
            assert d.action != Action.STOP


class TestLoopGuardState:
    """Test state management."""

    def test_reset_clears_state(self):
        guard = LoopGuard()
        for tool, args in EXACT_REPEAT_SCENARIO:
            guard.check(tool, args)
        assert guard.step_count > 0
        assert guard.consecutive_hits > 0

        guard.reset()
        assert guard.step_count == 0
        assert guard.consecutive_hits == 0

    def test_step_counter_increments(self):
        guard = LoopGuard()
        guard.check("tool_a", {})
        guard.check("tool_b", {})
        guard.check("tool_c", {})
        assert guard.step_count == 3

    def test_decision_has_step_number(self):
        guard = LoopGuard()
        d1 = guard.check("tool_a", {})
        d2 = guard.check("tool_b", {})
        assert d1.step_number == 1
        assert d2.step_number == 2

    def test_two_guards_independent(self):
        g1 = LoopGuard()
        g2 = LoopGuard()

        for tool, args in EXACT_REPEAT_SCENARIO:
            g1.check(tool, args)

        # g2 should have no detections
        d = g2.check("new_tool", {})
        assert d.action == Action.CONTINUE
        assert g2.step_count == 1


class TestActionConfig:
    """Test escalation thresholds."""

    def test_default_thresholds(self):
        config = ActionConfig()
        assert config.resolve_action(0) == Action.CONTINUE
        assert config.resolve_action(1) == Action.CONTINUE
        assert config.resolve_action(2) == Action.WARN
        assert config.resolve_action(4) == Action.STOP
        assert config.resolve_action(6) == Action.ESCALATE

    def test_custom_thresholds(self):
        config = ActionConfig(warn_threshold=1, stop_threshold=2, escalate_threshold=3)
        assert config.resolve_action(0) == Action.CONTINUE
        assert config.resolve_action(1) == Action.WARN
        assert config.resolve_action(2) == Action.STOP
        assert config.resolve_action(3) == Action.ESCALATE

    def test_escalation_in_guard(self):
        config = ActionConfig(warn_threshold=1, stop_threshold=3, escalate_threshold=5)
        guard = LoopGuard(window_size=5, action_config=config)

        actions = []
        for tool, args in EXACT_REPEAT_SCENARIO:
            d = guard.check(tool, args)
            actions.append(d.action)

        # Should see escalation over time
        assert Action.CONTINUE in actions  # starts with CONTINUE
        # Eventually should escalate
        assert any(a in (Action.WARN, Action.STOP, Action.ESCALATE) for a in actions)


class TestDecision:
    """Test Decision dataclass."""

    def test_is_loop_property(self):
        assert Decision(Action.STOP, "test").is_loop
        assert Decision(Action.ESCALATE, "test").is_loop
        assert not Decision(Action.CONTINUE, "test").is_loop
        assert not Decision(Action.WARN, "test").is_loop

    def test_should_warn_property(self):
        assert Decision(Action.WARN, "test").should_warn
        assert not Decision(Action.STOP, "test").should_warn
        assert not Decision(Action.CONTINUE, "test").should_warn

    def test_decision_fields(self):
        d = Decision(
            action=Action.STOP,
            reason="test reason",
            strategy="exact_repeat",
            confidence=0.95,
            step_number=5,
        )
        assert d.action == Action.STOP
        assert d.reason == "test reason"
        assert d.strategy == "exact_repeat"
        assert d.confidence == 0.95
        assert d.step_number == 5
