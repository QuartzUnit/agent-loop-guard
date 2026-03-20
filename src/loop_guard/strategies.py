"""Detection strategies for identifying loop patterns.

Each strategy implements a `check()` method that returns a confidence score
(0.0 = no loop, 1.0 = definite loop) and an explanation string.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from loop_guard.similarity import args_similarity


@dataclass
class ActionRecord:
    """A single agent action in the history."""

    tool: str
    args: dict | str | None = None
    output: str | None = None
    step: int = 0


# ---------------------------------------------------------------------------
# Strategy 1: Exact Repeat
# ---------------------------------------------------------------------------

@dataclass
class ExactRepeatStrategy:
    """Detect exact (tool, args) repetitions within the window."""

    window_size: int = 5

    _history: deque[ActionRecord] = field(default_factory=deque, init=False, repr=False)

    def check(self, record: ActionRecord) -> tuple[float, str]:
        """Returns (confidence, reason). 1.0 if last N actions are identical."""
        self._history.append(record)
        if len(self._history) > self.window_size:
            self._history.popleft()

        if len(self._history) < 2:
            return 0.0, ""

        # Check if all actions in window are identical
        first = self._history[0]
        all_same = all(
            r.tool == first.tool and r.args == first.args
            for r in self._history
        )

        if all_same and len(self._history) >= self.window_size:
            return 1.0, f"Exact repeat: '{first.tool}' called {len(self._history)} times with identical args"

        # Check consecutive repeats
        prev = self._history[-2]
        if record.tool == prev.tool and record.args == prev.args:
            # Count consecutive
            count = 0
            for r in reversed(self._history):
                if r.tool == record.tool and r.args == record.args:
                    count += 1
                else:
                    break
            confidence = min(1.0, count / self.window_size)
            return confidence, f"Exact repeat: '{record.tool}' repeated {count} times consecutively"

        return 0.0, ""

    def reset(self) -> None:
        self._history.clear()


# ---------------------------------------------------------------------------
# Strategy 2: Fuzzy Repeat
# ---------------------------------------------------------------------------

@dataclass
class FuzzyRepeatStrategy:
    """Detect near-identical actions using similarity scoring."""

    window_size: int = 5
    similarity_threshold: float = 0.85

    _history: deque[ActionRecord] = field(default_factory=deque, init=False, repr=False)

    def check(self, record: ActionRecord) -> tuple[float, str]:
        self._history.append(record)
        if len(self._history) > self.window_size:
            self._history.popleft()

        if len(self._history) < 2:
            return 0.0, ""

        # Compare current with all previous in window
        high_sim_count = 0
        max_sim = 0.0
        for prev in list(self._history)[:-1]:
            if record.tool != prev.tool:
                continue
            sim = args_similarity(record.args, prev.args)
            max_sim = max(max_sim, sim)
            if sim >= self.similarity_threshold:
                high_sim_count += 1

        if high_sim_count == 0:
            return 0.0, ""

        confidence = min(1.0, high_sim_count / (self.window_size - 1))
        return confidence, (
            f"Fuzzy repeat: '{record.tool}' similar to {high_sim_count} recent calls "
            f"(max similarity: {max_sim:.2f})"
        )

    def reset(self) -> None:
        self._history.clear()


# ---------------------------------------------------------------------------
# Strategy 3: Cycle Detection (A→B→C→A→B→C)
# ---------------------------------------------------------------------------

@dataclass
class CycleDetectionStrategy:
    """Detect repeating cycles of tool sequences (e.g., A→B→C→A→B→C)."""

    max_cycle_length: int = 5
    min_repetitions: int = 2

    _tool_sequence: list[str] = field(default_factory=list, init=False, repr=False)

    def check(self, record: ActionRecord) -> tuple[float, str]:
        self._tool_sequence.append(record.tool)

        # Need at least 2 * min_cycle_length to detect
        min_needed = 2 * 2  # min cycle of 2, repeated twice
        if len(self._tool_sequence) < min_needed:
            return 0.0, ""

        # Try cycle lengths from 2 to max_cycle_length
        seq = self._tool_sequence
        best_confidence = 0.0
        best_reason = ""

        for cycle_len in range(2, self.max_cycle_length + 1):
            if len(seq) < cycle_len * self.min_repetitions:
                continue

            # Extract the potential cycle pattern from the tail
            pattern = seq[-cycle_len:]

            # Skip degenerate patterns where all tools are the same
            # (that's repetition, not a cycle — handled by ExactRepeatStrategy)
            if len(set(pattern)) < 2:
                continue

            # Count how many times this pattern repeats backwards
            reps = 0
            for i in range(len(seq) - cycle_len, -1, -cycle_len):
                segment = seq[i : i + cycle_len]
                if segment == pattern:
                    reps += 1
                else:
                    break

            if reps >= self.min_repetitions:
                confidence = min(1.0, reps / (self.min_repetitions + 2))
                cycle_str = " → ".join(pattern)
                reason = f"Cycle detected: [{cycle_str}] repeated {reps} times"
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_reason = reason

        # Trim sequence to prevent unbounded growth
        max_len = self.max_cycle_length * (self.min_repetitions + 3)
        if len(self._tool_sequence) > max_len:
            self._tool_sequence = self._tool_sequence[-max_len:]

        return best_confidence, best_reason

    def reset(self) -> None:
        self._tool_sequence.clear()


# ---------------------------------------------------------------------------
# Strategy 4: Output Stagnation
# ---------------------------------------------------------------------------

@dataclass
class OutputStagnationStrategy:
    """Detect when tool outputs stop changing (agent is not making progress)."""

    window_size: int = 4
    similarity_threshold: float = 0.90

    _outputs: deque[tuple[str, str]] = field(default_factory=deque, init=False, repr=False)

    def check(self, record: ActionRecord) -> tuple[float, str]:
        if record.output is None:
            return 0.0, ""

        self._outputs.append((record.tool, record.output))
        if len(self._outputs) > self.window_size:
            self._outputs.popleft()

        if len(self._outputs) < 2:
            return 0.0, ""

        # Compare outputs for same tool
        same_tool_outputs = [o for t, o in self._outputs if t == record.tool]
        if len(same_tool_outputs) < 2:
            return 0.0, ""

        # Check if outputs are stagnant
        stagnant_count = 0
        for prev_out in same_tool_outputs[:-1]:
            sim = args_similarity(prev_out, record.output)
            if sim >= self.similarity_threshold:
                stagnant_count += 1

        if stagnant_count == 0:
            return 0.0, ""

        confidence = min(1.0, stagnant_count / (len(same_tool_outputs) - 1))
        return confidence, (
            f"Output stagnation: '{record.tool}' returned similar output "
            f"{stagnant_count + 1} times (threshold: {self.similarity_threshold:.2f})"
        )

    def reset(self) -> None:
        self._outputs.clear()
