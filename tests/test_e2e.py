"""End-to-end tests — realistic agent loop scenarios."""

from loop_guard import Action, ActionConfig, LoopGuard
from loop_guard.integrations.generic import LoopGuardCallback


class TestRealWorldScenarios:
    """Simulate actual agent loop patterns from production issues."""

    def test_crewai_4682_search_loop(self):
        """CrewAI #4682: Agent keeps searching for the same thing with minor variations."""
        # Lower similarity threshold — these are paraphrased queries, not exact repeats
        guard = LoopGuard(window_size=5, similarity_threshold=0.7)
        actions = [
            ("web_search", {"query": "python async best practices"}),
            ("web_search", {"query": "python async best practices 2024"}),
            ("web_search", {"query": "python async best practices tutorial"}),
            ("web_search", {"query": "python async best practices guide"}),
            ("web_search", {"query": "python async best practices examples"}),
            ("web_search", {"query": "python async best practices complete guide"}),
            ("web_search", {"query": "python async best practices advanced"}),
        ]
        had_warning = False
        for tool, args in actions:
            d = guard.check(tool, args)
            if d.action in (Action.WARN, Action.STOP, Action.ESCALATE):
                had_warning = True
        assert had_warning, "Should detect fuzzy search repetition"

    def test_aider_4828_edit_loop(self):
        """Aider #4828: Agent keeps editing the same file with same fix."""
        guard = LoopGuard(window_size=5)
        actions = [
            ("edit_file", {"path": "main.py", "content": "def fix(): pass"}),
            ("run_tests", {}, "FAIL: test_main"),
            ("edit_file", {"path": "main.py", "content": "def fix(): return True"}),
            ("run_tests", {}, "FAIL: test_main"),
            ("edit_file", {"path": "main.py", "content": "def fix(): return None"}),
            ("run_tests", {}, "FAIL: test_main"),
            ("edit_file", {"path": "main.py", "content": "def fix(): return False"}),
            ("run_tests", {}, "FAIL: test_main"),
            ("edit_file", {"path": "main.py", "content": "def fix(): return 0"}),
            ("run_tests", {}, "FAIL: test_main"),
        ]
        detected_cycle = False
        detected_stagnation = False
        for item in actions:
            tool, args = item[0], item[1]
            output = item[2] if len(item) > 2 else None
            d = guard.check(tool, args, output)
            if d.strategy == "cycle_detection" and d.confidence > 0:
                detected_cycle = True
            if d.strategy == "output_stagnation" and d.confidence > 0:
                detected_stagnation = True

        assert detected_cycle or detected_stagnation, "Should detect edit→test cycle or test stagnation"

    def test_openhands_stuck_on_error(self):
        """Agent retries the exact same command after error."""
        guard = LoopGuard(window_size=5)
        actions = [
            ("bash", {"command": "pip install broken-package"}, "ERROR: No matching distribution"),
            ("bash", {"command": "pip install broken-package"}, "ERROR: No matching distribution"),
            ("bash", {"command": "pip install broken-package"}, "ERROR: No matching distribution"),
            ("bash", {"command": "pip install broken-package"}, "ERROR: No matching distribution"),
            ("bash", {"command": "pip install broken-package"}, "ERROR: No matching distribution"),
        ]
        loop_detected = False
        for tool, args, output in actions:
            d = guard.check(tool, args, output)
            if d.is_loop:
                loop_detected = True
                break
        assert loop_detected

    def test_legitimate_long_refactoring(self):
        """Agent reading many files for refactoring — should NOT trigger."""
        guard = LoopGuard(window_size=10)
        actions = [
            ("read_file", {"path": f"src/module_{i}.py"}) for i in range(15)
        ] + [
            ("search", {"query": "deprecated_function", "path": f"src/module_{i}.py"})
            for i in range(15)
        ] + [
            ("edit_file", {"path": f"src/module_{i}.py", "content": f"# refactored {i}"})
            for i in range(15)
        ]
        for tool, args in actions:
            d = guard.check(tool, args)
            assert d.action != Action.STOP, f"False positive at step {d.step_number}: {d.reason}"

    def test_legitimate_data_processing(self):
        """Agent processing different data files — should NOT trigger."""
        guard = LoopGuard(window_size=10)
        for i in range(20):
            d = guard.check("process_file", {"input": f"data_{i}.csv", "output": f"result_{i}.json"})
            assert not d.is_loop, f"False positive at step {d.step_number}"

    def test_callback_integration_flow(self):
        """Full callback flow with warn→stop escalation."""
        warnings = []
        stops = []
        callback = LoopGuardCallback(
            window_size=5,
            on_warn=lambda d: warnings.append(d.reason),
            on_stop=lambda d: stops.append(d.reason),
        )

        # Normal actions
        callback.before_tool_call("read", {"path": "a.py"})
        callback.before_tool_call("edit", {"path": "a.py"})
        assert len(warnings) == 0

        # Start looping
        for _ in range(10):
            callback.before_tool_call("search", {"query": "fix error"})

        # Should have accumulated warnings then stops
        assert len(warnings) > 0 or len(stops) > 0

    def test_mixed_tools_then_loop(self):
        """Normal diverse usage, then one tool starts looping."""
        guard = LoopGuard(window_size=5)

        # Diverse normal usage
        normal = [
            ("plan", {"task": "refactor auth"}),
            ("search", {"query": "auth middleware patterns"}),
            ("read_file", {"path": "auth.py"}),
            ("edit_file", {"path": "auth.py", "content": "new auth code"}),
            ("run_tests", {}),
        ]
        for tool, args in normal:
            d = guard.check(tool, args)
            assert d.action == Action.CONTINUE

        # Now start looping on search
        loop_detected = False
        for i in range(10):
            d = guard.check("search", {"query": "auth error fix"})
            if d.action in (Action.WARN, Action.STOP):
                loop_detected = True
                break
        assert loop_detected

    def test_custom_config_aggressive(self):
        """Aggressive detection config — warn on first repeat."""
        config = ActionConfig(warn_threshold=1, stop_threshold=2, escalate_threshold=3)
        guard = LoopGuard(window_size=3, action_config=config)

        guard.check("search", {"q": "test"})
        d = guard.check("search", {"q": "test"})
        # With aggressive config, should warn quickly
        # May need a few more checks to accumulate
        guard.check("search", {"q": "test"})
        d = guard.check("search", {"q": "test"})
        assert d.action in (Action.WARN, Action.STOP, Action.ESCALATE)
