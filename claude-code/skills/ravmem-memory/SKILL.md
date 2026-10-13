---
name: ravmem-memory
description: Persist, recall, and curate task context, architectural decisions, and learnings across sessions in this team's RavMem knowledge graph. Use at the start of work to load standing instructions, while working to record decisions and gotchas, and when handing a session to another tool.
allowed-tools: ["mcp__ravmem__memory_load_context", "mcp__ravmem__memory_search", "mcp__ravmem__memory_get", "mcp__ravmem__memory_list", "mcp__ravmem__memory_task", "mcp__ravmem__memory_record", "mcp__ravmem__memory_link_code", "mcp__ravmem__memory_review", "mcp__ravmem__memory_update"]
---

RavMem memory is shared by the team and survives across sessions and tools. Authorship comes from your
token. The memory team and branch come from the `X-KG-Team` / `X-KG-Branch` headers in the MCP client
config (defaults `default` and `global`), so you never pass them as arguments.

### Start of a session
1. `memory_load_context()` with no arguments returns the standing instructions (critical first) and
   conditions. Follow them.
2. `memory_list(node_type="Task")` shows tasks still open. Resume one with `memory_load_context(task_id)`,
   which returns that task's instructions, learnings, decisions, blockers, context and linked code symbols.
3. Starting something new that is worth tracking: `memory_task(action="start", label, task_type, repo_id,
   git_branch)` and keep the returned task id.

### While working
- `memory_record(kind="decision", task_id, choice, rationale, alternatives)` — a choice that was made and
  why ("we decided…", "let's go with X").
- `memory_record(kind="learning", task_id, content, domain)` — a non-obvious gotcha, constraint or
  performance finding a future session would otherwise rediscover.
- `memory_record(kind="context", content, context_type)` — environment or config facts;
  `expires_in_hours` for anything temporary.
- `memory_task(action="block", task_id, description, severity)` and
  `memory_task(action="resolve_blocker", blocker_id, resolution)` — track and clear blockers.
- `memory_link_code(node_id, symbol_ids)` — attach a node to the code it is about, so it surfaces when
  that code is edited. Symbol ids come from `code_search`.
- `memory_task(action="complete", task_id, outcome)` when the work ends.

### Looking things up
`memory_search(query)` finds nodes by meaning; `memory_get(node_id)` returns one node with its links;
`memory_list` browses by type or scope.

### Curating
- `memory_review(action="corroborate", learning_id, task_id)` — a task confirmed an existing learning.
- `memory_review(action="validate" | "promote", ...)` need the `kg:validate` permission. Validate before
  promoting a learning to a permanent instruction.
- `memory_update(node_id, properties)` edits a node; `memory_update(node_id, deactivate=true)` retires
  one that is outdated.

### Handing a session to another tool
There is no transfer token. Before you stop, record what the next session needs — the current task
(`memory_task`), settled decisions, open blockers, and a `memory_record(kind="context")` note listing the
active files and next steps. The next tool starts with `memory_list(node_type="Task")` and
`memory_load_context(task_id)` and picks up from there.

### Prompts
The server also offers MCP prompts: `session_start`, `pre_edit_impact`, `onboard_repo`,
`session_handoff` and `review_learnings`. Clients that list prompts (Claude Code shows them as slash
commands) can run these as ready-made versions of the workflows above.
