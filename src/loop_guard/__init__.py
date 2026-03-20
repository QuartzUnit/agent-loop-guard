"""agent-loop-guard — Framework-agnostic agent loop detection.

Sliding window similarity scoring to catch stuck agents.
"""

from loop_guard.decision import Action, ActionConfig, Decision
from loop_guard.guard import LoopGuard
from loop_guard.strategies import ActionRecord

__all__ = ["LoopGuard", "Action", "ActionConfig", "Decision", "ActionRecord"]
__version__ = "0.1.0"
