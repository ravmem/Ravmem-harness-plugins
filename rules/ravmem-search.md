---
description: Search and navigate codebase symbols, classes and files with the RavMem code graph instead of grep
always_on: true
---

# Code-Graph Search & Navigation (RavMem)

Prefer these RavMem tools over grep/find for structural questions about an indexed repo.

**Every code tool needs a `project`.** Call `projects_list` once to get the project id (it also shows
each branch's index state), then pass that id to the other code tools. The branch defaults to the
project's default branch; pass `branch` to look at another one.

- `code_search(project, query)` — hybrid keyword + semantic search over functions, classes and methods.
  Use it first when you don't know the file or symbol id. Each hit carries the id the other tools take.
- `code_get_symbol(project, symbol_id)` — one symbol in full: signature, location, callers, callees and
  cluster peers.
- `code_get_symbol(project, file_path)` — every symbol in a file; add `prefix=true` for a directory, and
  `detail="full"` to include callers/callees per symbol. The right first call on an unfamiliar file.
- `code_relations(project, symbol_id)` — what a class extends and what extends it.
  `code_relations(project, file_path)` — the files it imports and the files that import it.
- `code_explore(project, kind)` — `clusters` lists module groups, `cluster` (with `cluster_id`) lists one
  group's members, `entry_points` lists the most central symbols. Use it to get oriented in a new repo.

Results are limited (`limit`) and say when they were truncated; narrow the query or raise the limit
rather than assuming you saw everything.

Fall back to plain grep only for exact string literals, log messages, or non-code files. If a call fails
with an auth or connection error, surface it instead of retrying silently. If the project isn't in
`projects_list`, it hasn't been indexed — see the onboarding guidance.
