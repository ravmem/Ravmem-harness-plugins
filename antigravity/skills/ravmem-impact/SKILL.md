---
name: ravmem-impact
description: Check blast radius before editing a function, class, or shared module in an indexed repo — use before modifying widely-used code to see callers, callees, and which clusters/tests might break, instead of guessing from a single file's contents.
allowed-tools: ["mcp__ravmem__projects_list", "mcp__ravmem__code_search", "mcp__ravmem__code_impact", "mcp__ravmem__code_call_chain", "mcp__ravmem__code_relations", "mcp__ravmem__code_explore"]
---

Before changing a symbol that looks shared (exported, called from several files, or central to a
cluster), check what depends on it. Get the symbol id from `code_search` first.

- `code_impact(project, symbol_id, depth=3)` — direct and transitive callers of the symbol: the main
  "what breaks if I change this" check.
- `code_impact(project, diff=<unified diff>)` — the same analysis for a whole change set: it works out
  which functions and classes the diff touches and reports each one's blast radius. Use it when
  reviewing an edit or a branch rather than one symbol.
- `code_call_chain(project, symbol_id, direction="callers" | "callees" | "both")` — follow the call
  graph further than the immediate blast radius.
- `code_relations(project, symbol_id)` — for a class, what extends it; for a file
  (`file_path`), what imports it. Impact through inheritance and imports shows up here.
- `code_explore(project, kind="cluster", cluster_id=...)` — the module a symbol belongs to and its peers.

Run this **before** making the edit — the point is to inform the change, not to document it afterwards.
If the impact is large (many callers across clusters), say so explicitly before proceeding instead of
editing silently, and list the call sites the edit needs to cover. Results are truncated at `limit`;
a truncated result means there are more affected symbols than listed.
