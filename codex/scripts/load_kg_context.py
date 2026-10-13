#!/usr/bin/env python3
"""SessionStart hook: print the team's open RavMem tasks so the model starts with them in context.

Only the task list is loaded (not every memory node) to keep the context small. The model loads one task's
full context on demand with the `memory_load_context` tool.

Silent (exit 0, no output) when auto-load is disabled (RAVMEM_KG_AUTO_LOAD=false), the server is
unreachable or rejects the token, or there are no open tasks. A hook must never break a session start.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ravmem_http import RavMemError, list_nodes, setting  # noqa: E402

MAX_TASKS = 10


def main() -> int:
    if (setting("KG_AUTO_LOAD") or "true").lower() in ("false", "0", "no", "off"):
        return 0
    try:
        tasks = list_nodes("Task", active_only=True, timeout=3.0)
    except RavMemError:
        return 0
    if not tasks:
        return 0

    lines = ["[RavMem] Open tasks for this team:"]
    for t in tasks[:MAX_TASKS]:
        props = t.get("properties") or {}
        task_type = props.get("task_type") or t.get("task_type") or "task"
        lines.append(f"  - [{t.get('id', '?')}] {t.get('label') or 'Untitled task'} (type: {task_type})")
    if len(tasks) > MAX_TASKS:
        lines.append(f"  ... and {len(tasks) - MAX_TASKS} more (memory_list with node_type=\"Task\").")
    lines.append("Load one with the memory_load_context tool (task_id). Standing instructions: memory_load_context with no arguments.")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
