#!/usr/bin/env python3
"""Generate every harness's skills/rules from one source of truth.

The plugins talk to the RavMem server over its standard MCP endpoint
(Streamable HTTP at <server>/mcp); there is no local adapter. What differs per
harness is only the file format around the same guidance, so the guidance lives
here once and this script writes:

  claude-code/skills/*/SKILL.md      claude-desktop/skills/*/SKILL.md
  antigravity/skills/*/SKILL.md      antigravity/rules/*.md
  cursor/rules/*.mdc                 codex/AGENTS.md(.fragment)
  antigravity/GEMINI.md(.fragment)
  <harness>/scripts/{_ravmem_http,load_kg_context,prune_kg,check_onboarding}.py  (copied from core/scripts)

Run:  python3 build_content.py          (rewrites the files)
      python3 build_content.py --check  (exit 1 if any file is out of date)

Tool names are the server's 18 MCP tools. Source of truth for them:
GET <server>/api/mcp/tools.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREFIX = "mcp__ravmem__"  # Claude-style tool id: mcp__<server name>__<tool>

BEGIN = "<!-- BEGIN RAVMEM INSTRUCTIONS -->"
END = "<!-- END RAVMEM INSTRUCTIONS -->"

TOPICS = {
    "ravmem-search": {
        "tools": ["projects_list", "code_search", "code_get_symbol", "code_relations", "code_explore"],
        "skill_description": (
            "Search and navigate this codebase's indexed symbols, call graphs, and file context via RavMem "
            "instead of grep/find, when the repo has already been indexed. Use for \"find where X is defined\", "
            "\"what's in this file/directory\", \"what extends/imports Y\", or any structural code-navigation "
            "question that a graph index answers faster and more precisely than text search."
        ),
        "rule_description": "Search and navigate codebase symbols, classes and files with the RavMem code graph instead of grep",
        "title": "Code-Graph Search & Navigation (RavMem)",
        "body": """\
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
`projects_list`, it hasn't been indexed — see the onboarding guidance.""",
    },
    "ravmem-impact": {
        "tools": ["projects_list", "code_search", "code_impact", "code_call_chain", "code_relations", "code_explore"],
        "skill_description": (
            "Check blast radius before editing a function, class, or shared module in an indexed repo — use "
            "before modifying widely-used code to see callers, callees, and which clusters/tests might break, "
            "instead of guessing from a single file's contents."
        ),
        "rule_description": "Check the blast radius of a change with the RavMem code graph before editing shared code",
        "title": "Blast Radius & Impact Analysis (RavMem)",
        "body": """\
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
a truncated result means there are more affected symbols than listed.""",
    },
    "ravmem-memory": {
        "tools": [
            "memory_load_context", "memory_search", "memory_get", "memory_list", "memory_task",
            "memory_record", "memory_link_code", "memory_review", "memory_update",
        ],
        "skill_description": (
            "Persist, recall, and curate task context, architectural decisions, and learnings across sessions "
            "in this team's RavMem knowledge graph. Use at the start of work to load standing instructions, "
            "while working to record decisions and gotchas, and when handing a session to another tool."
        ),
        "rule_description": "Persist, recall and curate task context, decisions and learnings across sessions in RavMem memory",
        "title": "Knowledge Graph Memory Continuity (RavMem)",
        "body": """\
RavMem memory is shared by the team and survives across sessions and tools. Authorship comes from your
token. The memory team and branch come from the `X-KG-Team` / `X-KG-Branch` headers in the MCP client
config (defaults `default` and `global`), so you never pass them as arguments.

### Start of a session
1. `memory_load_context()` with no arguments returns the standing instructions (critical first) and
   conditions. Follow them.
2. `memory_list(node_type="Task")` shows tasks still in progress; add `include_completed=true` to see
   finished ones. To resume a task, call `memory_load_context(task_id)`: it returns the learnings, decisions
   and open blockers recorded for that task, the standing instructions and conditions that apply to it,
   validated learnings and decisions from similar past tasks, and the code symbols they are linked to.
   `memory_get(task_id)` shows the same records as graph links.
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
active files and next steps (give the note a clear label naming the task). The next tool finds the task with
`memory_list(node_type="Task")`, reads what was recorded with `memory_load_context(task_id)`, and uses
`memory_search` for the context note.

### Prompts
The server also offers MCP prompts: `session_start`, `pre_edit_impact`, `onboard_repo`,
`session_handoff` and `review_learnings`. Clients that list prompts (Claude Code shows them as slash
commands) can run these as ready-made versions of the workflows above.""",
    },
    "ravmem-status": {
        "tools": ["projects_list", "project_sync", "jobs"],
        "skill_description": (
            "Check RavMem project/branch index status and background job health — use for diagnostics, "
            "before trusting search/impact results right after a big change or branch switch, or when the "
            "user asks whether RavMem is working."
        ),
        "rule_description": "Check RavMem index freshness and background job health before trusting stale results",
        "title": "Index Status & Diagnostics (RavMem)",
        "body": """\
Use for diagnostics, not routine navigation.

- `projects_list()` — every project with each branch's index status. A branch must be `ready` before the
  code tools can use it. Check it before relying on search or impact results right after switching
  branches or a large merge, and say so if the index is behind the code before answering from it.
- `project_sync(project, branch?, mode="auto")` — bring the index up to date. It fetches new commits for
  projects the server has cloned and re-indexes only what changed. It waits up to `wait_seconds`
  (default 20, max 50) and reports progress; if the job is still running it returns the job id.
  For a project uploaded from a laptop there is no remote to fetch: `project_sync` only re-indexes the files
  already stored on the server, so new local commits need `ravmem analyze . --project <project> --incremental
  --wait` from the repo.
- `jobs(job_id)` — one job's status and progress; `jobs(project=…, branch=…)` — recent jobs. Use it to
  see whether an indexing job is running, failed or stuck, especially after onboarding or a re-index.

If a call fails with a licensing error, tell the user; do not retry. Fix an unhealthy index with
`project_sync`, then confirm with `jobs`; don't answer from outdated results.""",
    },
    "ravmem-onboarding": {
        "tools": ["projects_list", "project_sync", "jobs"],
        "skill_description": (
            "Set up RavMem for this repo for the first time — registers the project and indexes it. "
            "User-invoked only; not something to trigger automatically mid-task."
        ),
        "rule_description": "Index this repository in RavMem for the first time (user-invoked)",
        "title": "First-Time Repository Onboarding (RavMem)",
        "skill_extra": 'disable-model-invocation: true\n',
        "body": """\
Indexing a repository from a developer machine is done with the RavMem CLI, because it reads the
local git repo and uploads its **committed** files; an MCP server cannot read your disk.

1. Check whether the repo is already indexed: `projects_list()`. If the project is there and its default
   branch is ready, you are done — use the search and impact guidance.
2. Otherwise ask the user to run, from the repo root:

   ```
   pip install ravmem-cli                       # once
   ravmem remote add . --name <project>         # registers the project (once per repo)
   ravmem analyze . --project <project> --wait  # uploads the committed files and indexes them
   ```

   `remote add` must come first: `analyze` fails with "Project not found" for an unregistered project. Add
   `--langs python,typescript` to `analyze` to limit languages. The CLI reads the server URL and token from
   `~/.ravmem/client.json` (`ravmem auth login` writes it), or accept `--remote <url>`. If your branch is not
   the project's default branch (for example `master` while the project says `main`), the code tools answer
   "Branch … has no index" and list the available branches; pass `branch` or fix the default with
   `ravmem remote` / `PATCH /api/projects/<id>`.
3. Requirements: the repo is a git repository with at least one commit. Uncommitted changes are not
   uploaded; if the CLI reports "no committed files", commit first.
4. Confirm with `projects_list()` and `jobs(project=…)`. Later updates are `ravmem analyze . --project <project>
   --incremental` from the repo; `project_sync` also works for projects the server cloned itself.

Do not run the CLI for the user unprompted — it uploads source code to the server.""",
    },
}


def _tool_ids(tools: list[str]) -> str:
    return "[" + ", ".join(f'"{PREFIX}{t}"' for t in tools) + "]"


def skill_md(name: str, t: dict) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {t['skill_description']}\n"
        f"{t.get('skill_extra', '')}"
        f"allowed-tools: {_tool_ids(t['tools'])}\n"
        "---\n\n"
        f"{t['body']}\n"
    )


def cursor_mdc(name: str, t: dict) -> str:
    return (
        "---\n"
        f"description: {t['rule_description']}\n"
        "globs: *\n"
        "alwaysApply: true\n"
        "---\n\n"
        f"# {t['title']}\n\n"
        f"{t['body']}\n"
    )


def antigravity_rule(name: str, t: dict) -> str:
    return (
        "---\n"
        f"description: {t['rule_description']}\n"
        "always_on: true\n"
        "---\n\n"
        f"# {t['title']}\n\n"
        f"{t['body']}\n"
    )


def _demote(body: str) -> str:
    """Turn '### x' headings into '#### x' so topics nest under a '### topic' heading."""
    return "\n".join(("#" + line) if line.startswith("###") else line for line in body.splitlines())


def instructions_block(harness: str, config_key: str) -> str:
    parts = [
        BEGIN,
        "## RavMem Context Engine Integration",
        "",
        f"This {harness} is connected to a self-hosted RavMem server over MCP (`{config_key}.ravmem`, "
        "Streamable HTTP at `<server>/mcp`). Follow these rules when exploring, refactoring, or planning.",
        "",
    ]
    for i, name in enumerate(("ravmem-search", "ravmem-impact", "ravmem-memory", "ravmem-status", "ravmem-onboarding"), 1):
        t = TOPICS[name]
        parts += [f"### {i}. {t['title']}", "", _demote(t["body"]), ""]
    parts.append(END)
    return "\n".join(parts) + "\n"


def _splice(existing: str, block: str, header: str) -> str:
    if BEGIN in existing and END in existing:
        pre = existing.split(BEGIN)[0]
        post = existing.split(END, 1)[1]
        return pre + block.rstrip("\n") + post
    return header + "\n" + block


def targets() -> dict[Path, str]:
    out: dict[Path, str] = {}
    for name, t in TOPICS.items():
        for harness in ("claude-code", "claude-desktop", "antigravity"):
            out[ROOT / harness / "skills" / name / "SKILL.md"] = skill_md(name, t)
        out[ROOT / "cursor" / "rules" / f"{name}.mdc"] = cursor_mdc(name, t)
        out[ROOT / "antigravity" / "rules" / f"{name}.md"] = antigravity_rule(name, t)

    for src in sorted((ROOT / "core" / "scripts").glob("*.py")):
        for harness in ("claude-code", "claude-desktop", "antigravity", "cursor", "codex"):
            out[ROOT / harness / "scripts" / src.name] = src.read_text(encoding="utf-8")

    codex_block = instructions_block("project", "mcp_servers")
    ag_block = instructions_block("workspace", "mcpServers")
    out[ROOT / "codex" / "AGENTS.md.fragment"] = codex_block
    out[ROOT / "antigravity" / "GEMINI.md.fragment"] = ag_block
    for path, block, header in (
        (ROOT / "codex" / "AGENTS.md", codex_block,
         "# AGENTS.md\n\nInstructions and guidelines for AI coding agents working in this repository.\n"),
        (ROOT / "antigravity" / "GEMINI.md", ag_block,
         "# GEMINI.md\n\nAntigravity project rules and instructions.\n"),
    ):
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        out[path] = _splice(existing, block, header)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if any generated file is out of date")
    args = ap.parse_args()

    stale = []
    for path, content in targets().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        stale.append(path)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    verb = "out of date" if args.check else "written"
    for p in stale:
        print(f"{verb}: {p.relative_to(ROOT)}")
    if not stale:
        print("all generated files are up to date")
    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
