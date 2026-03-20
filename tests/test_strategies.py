"""Tests for individual detection strategies."""

from loop_guard.strategies import (
    ActionRecord,
    CycleDetectionStrategy,
    ExactRepeatStrategy,
    FuzzyRepeatStrategy,
    OutputStagnationStrategy,
)


class TestExactRepeat:
    def test_detects_consecutive_repeats(self):
        s = ExactRepeatStrategy(window_size=3)
        r = ActionRecord(tool="search", args={"q": "test"})
        s.check(r)
        s.check(r)
        conf, reason = s.check(r)
        assert conf > 0
        assert "search" in reason

    def test_no_detection_on_different_tools(self):
        s = ExactRepeatStrategy(window_size=3)
        conf1, _ = s.check(ActionRecord(tool="search", args={"q": "a"}))
        conf2, _ = s.check(ActionRecord(tool="read", args={"path": "b"}))
        conf3, _ = s.check(ActionRecord(tool="write", args={"path": "c"}))
        assert conf1 == 0 and conf2 == 0 and conf3 == 0

    def test_no_detection_on_same_tool_different_args(self):
        s = ExactRepeatStrategy(window_size=3)
        s.check(ActionRecord(tool="search", args={"q": "alpha"}))
        conf, _ = s.check(ActionRecord(tool="search", args={"q": "beta"}))
        assert conf == 0

    def test_reset(self):
        s = ExactRepeatStrategy(window_size=3)
        r = ActionRecord(tool="search", args={"q": "test"})
        s.check(r)
        s.check(r)
        s.reset()
        conf, _ = s.check(r)
        assert conf == 0  # fresh start


class TestFuzzyRepeat:
    def test_detects_similar_args(self):
        s = FuzzyRepeatStrategy(window_size=5, similarity_threshold=0.7)
        s.check(ActionRecord(tool="search", args={"q": "how to fix python error"}))
        s.check(ActionRecord(tool="search", args={"q": "how to fix python error code"}))
        conf, reason = s.check(ActionRecord(tool="search", args={"q": "how to fix the python error"}))
        assert conf > 0
        assert "similar" in reason.lower() or "Fuzzy" in reason

    def test_no_detection_on_different_tools(self):
        s = FuzzyRepeatStrategy(window_size=5, similarity_threshold=0.7)
        s.check(ActionRecord(tool="search", args={"q": "test query"}))
        conf, _ = s.check(ActionRecord(tool="read", args={"q": "test query"}))
        assert conf == 0  # different tools

    def test_no_detection_on_dissimilar_args(self):
        s = FuzzyRepeatStrategy(window_size=5, similarity_threshold=0.85)
        s.check(ActionRecord(tool="search", args={"q": "python tutorial"}))
        conf, _ = s.check(ActionRecord(tool="search", args={"q": "rust memory safety"}))
        assert conf == 0

    def test_string_args(self):
        s = FuzzyRepeatStrategy(window_size=5, similarity_threshold=0.6)
        s.check(ActionRecord(tool="bash", args="ls -la /home/user/documents"))
        conf, _ = s.check(ActionRecord(tool="bash", args="ls -la /home/user/downloads"))
        assert conf > 0

    def test_none_args(self):
        s = FuzzyRepeatStrategy(window_size=5, similarity_threshold=0.7)
        s.check(ActionRecord(tool="status", args=None))
        conf, _ = s.check(ActionRecord(tool="status", args=None))
        # None == None → exact match → similarity 1.0
        assert conf > 0


class TestCycleDetection:
    def test_detects_abc_cycle(self):
        s = CycleDetectionStrategy(max_cycle_length=5, min_repetitions=2)
        # A→B→C→A→B→C
        tools = ["read", "edit", "test", "read", "edit", "test"]
        results = []
        for t in tools:
            conf, reason = s.check(ActionRecord(tool=t))
            results.append((conf, reason))

        assert any(c > 0 for c, _ in results)
        assert any("Cycle" in r for _, r in results if r)

    def test_detects_ab_cycle(self):
        s = CycleDetectionStrategy(max_cycle_length=5, min_repetitions=2)
        # A→B→A→B
        tools = ["search", "read", "search", "read"]
        results = []
        for t in tools:
            conf, reason = s.check(ActionRecord(tool=t))
            results.append((conf, reason))

        assert any(c > 0 for c, _ in results)

    def test_no_cycle_in_diverse_sequence(self):
        s = CycleDetectionStrategy(max_cycle_length=5, min_repetitions=2)
        tools = ["a", "b", "c", "d", "e", "f", "g", "h"]
        for t in tools:
            conf, _ = s.check(ActionRecord(tool=t))
            assert conf == 0

    def test_longer_cycle(self):
        s = CycleDetectionStrategy(max_cycle_length=5, min_repetitions=2)
        # A→B→C→D→A→B→C→D
        pattern = ["plan", "search", "read", "write"]
        tools = pattern * 3
        results = []
        for t in tools:
            conf, _ = s.check(ActionRecord(tool=t))
            results.append(conf)

        assert any(c > 0 for c in results)

    def test_reset(self):
        s = CycleDetectionStrategy(max_cycle_length=5, min_repetitions=2)
        for t in ["a", "b", "a", "b"]:
            s.check(ActionRecord(tool=t))
        s.reset()
        conf, _ = s.check(ActionRecord(tool="a"))
        assert conf == 0


class TestOutputStagnation:
    def test_detects_same_output(self):
        s = OutputStagnationStrategy(window_size=4, similarity_threshold=0.9)
        output = "Error: test_login failed"
        s.check(ActionRecord(tool="test", output=output))
        s.check(ActionRecord(tool="test", output=output))
        conf, reason = s.check(ActionRecord(tool="test", output=output))
        assert conf > 0
        assert "stagnation" in reason.lower()

    def test_no_stagnation_with_different_outputs(self):
        s = OutputStagnationStrategy(window_size=4, similarity_threshold=0.9)
        s.check(ActionRecord(tool="test", output="PASS: 5 tests"))
        s.check(ActionRecord(tool="test", output="FAIL: 1 error"))
        conf, _ = s.check(ActionRecord(tool="test", output="PASS: 6 tests"))
        assert conf == 0

    def test_ignores_none_output(self):
        s = OutputStagnationStrategy(window_size=4, similarity_threshold=0.9)
        conf, _ = s.check(ActionRecord(tool="test", output=None))
        assert conf == 0

    def test_tracks_per_tool(self):
        s = OutputStagnationStrategy(window_size=4, similarity_threshold=0.9)
        s.check(ActionRecord(tool="test", output="FAIL"))
        s.check(ActionRecord(tool="search", output="results"))
        conf, _ = s.check(ActionRecord(tool="test", output="FAIL"))
        # Only 2 same-tool outputs, should still detect
        assert conf > 0

    def test_reset(self):
        s = OutputStagnationStrategy(window_size=4, similarity_threshold=0.9)
        s.check(ActionRecord(tool="test", output="FAIL"))
        s.check(ActionRecord(tool="test", output="FAIL"))
        s.reset()
        conf, _ = s.check(ActionRecord(tool="test", output="FAIL"))
        assert conf == 0  # fresh start
