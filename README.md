# agent-loop-guard

Framework-agnostic agent loop detection — sliding window similarity scoring to catch stuck agents.

## Install

```bash
pip install agent-loop-guard
```

## Quick Start

```python
from loop_guard import LoopGuard, Action

guard = LoopGuard()

for action in agent_actions:
    decision = guard.check(tool=action.name, args=action.args)
    if decision.action == Action.STOP:
        print(f"Loop detected: {decision.reason}")
        break
```

## Why not just `max_iter`?

| Approach | What it catches | Limitation |
|----------|----------------|------------|
| `max_iter=10` | Runaway agents | Kills long *legitimate* tasks; misses 3-step loops at step 9 |
| **agent-loop-guard** | Exact repeats, fuzzy repeats, A→B→C→A cycles, output stagnation | — |

`max_iter` is a blunt timeout. `agent-loop-guard` detects *behavioral patterns* — the agent doing the same thing over and over, even with slight variations.

## Detection Strategies

| Strategy | What it detects | Confidence signal |
|----------|----------------|-------------------|
| **Exact Repeat** | Same `(tool, args)` called repeatedly | Consecutive identical calls |
| **Fuzzy Repeat** | Near-identical args (Jaccard + edit distance) | Similarity > threshold |
| **Cycle Detection** | A→B→C→A→B→C repeating sequences | Pattern repetition count |
| **Output Stagnation** | Tool returns same output repeatedly | Output similarity > threshold |

All four strategies run on every call. The highest confidence wins.

## API

```python
guard = LoopGuard(
    window_size=10,             # actions to keep in memory
    similarity_threshold=0.85,  # fuzzy match threshold
)

decision = guard.check(
    tool="web_search",          # tool/function name
    args={"query": "python"},   # arguments (dict or str)
    output="Results: ...",      # optional: enables stagnation detection
)

decision.action       # Action.CONTINUE | WARN | STOP | ESCALATE
decision.reason       # "Cycle detected: [search → parse → search] repeated 3 times"
decision.strategy     # "cycle_detection"
decision.confidence   # 0.0 ~ 1.0
decision.is_loop      # True if STOP or ESCALATE
decision.should_warn  # True if WARN

guard.reset()         # reuse for next session
```

## Action Escalation

Actions escalate with consecutive detections:

```python
from loop_guard import ActionConfig

config = ActionConfig(
    warn_threshold=2,      # 2 consecutive hits → WARN
    stop_threshold=4,      # 4 consecutive hits → STOP
    escalate_threshold=6,  # 6 consecutive hits → ESCALATE
)

guard = LoopGuard(action_config=config)
```

## Generic Callback

```python
from loop_guard.integrations.generic import LoopGuardCallback

callback = LoopGuardCallback(
    on_warn=lambda d: logger.warning(f"Loop warning: {d.reason}"),
    on_stop=lambda d: raise_stop_error(d),
)

# In your agent loop:
decision = callback.before_tool_call("search", {"query": "test"})
```

## License

MIT
