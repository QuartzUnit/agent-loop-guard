"""Test fixtures — realistic agent loop scenarios."""

# Exact repeat: agent calls same search over and over
EXACT_REPEAT_SCENARIO = [
    ("web_search", {"query": "python tutorial"}),
    ("web_search", {"query": "python tutorial"}),
    ("web_search", {"query": "python tutorial"}),
    ("web_search", {"query": "python tutorial"}),
    ("web_search", {"query": "python tutorial"}),
    ("web_search", {"query": "python tutorial"}),
]

# Fuzzy repeat: same tool, slightly different args
FUZZY_REPEAT_SCENARIO = [
    ("web_search", {"query": "how to fix error in python"}),
    ("web_search", {"query": "how to fix error in python code"}),
    ("web_search", {"query": "how to fix the error in python"}),
    ("web_search", {"query": "fix error in python programming"}),
    ("web_search", {"query": "how to fix python error"}),
]

# Cycle: A→B→C→A→B→C
CYCLE_SCENARIO = [
    ("read_file", {"path": "main.py"}),
    ("edit_file", {"path": "main.py", "content": "fix1"}),
    ("run_tests", {}),
    ("read_file", {"path": "main.py"}),
    ("edit_file", {"path": "main.py", "content": "fix2"}),
    ("run_tests", {}),
    ("read_file", {"path": "main.py"}),
    ("edit_file", {"path": "main.py", "content": "fix3"}),
    ("run_tests", {}),
]

# Output stagnation: tool returns same output
STAGNATION_SCENARIO = [
    ("run_tests", {}, "FAILED: test_login (AssertionError)"),
    ("run_tests", {}, "FAILED: test_login (AssertionError)"),
    ("run_tests", {}, "FAILED: test_login (AssertionError)"),
    ("run_tests", {}, "FAILED: test_login (AssertionError)"),
]

# Normal operation: diverse tool usage
NORMAL_SCENARIO = [
    ("web_search", {"query": "python asyncio tutorial"}),
    ("read_file", {"path": "server.py"}),
    ("edit_file", {"path": "server.py", "content": "async def handler():\n    pass"}),
    ("run_tests", {}),
    ("web_search", {"query": "fastapi middleware"}),
    ("read_file", {"path": "middleware.py"}),
    ("edit_file", {"path": "middleware.py", "content": "class AuthMiddleware:\n    pass"}),
    ("run_tests", {}),
]

# Long legitimate task: many steps but making progress
LONG_NORMAL_SCENARIO = [
    ("read_file", {"path": f"module_{i}.py"})
    for i in range(20)
] + [
    ("web_search", {"query": f"refactor pattern {i}"})
    for i in range(5)
]
