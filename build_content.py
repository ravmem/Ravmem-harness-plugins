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
  claude-code/commands/*.md   cursor/commands/*.md   codex/prompts/*.md   antigravity/skills/ravmem-{setup,configure}/  claude-desktop/skills/ravmem-{setup,configure}/
  plugin.json, skills/, rules/ at the repo root   (the repo root is an installable Antigravity plugin; no MCP config)
  <harness> ravmem-setup / ravmem-configure commands, prompts and skills (guided server install and connect)
  <harness>/scripts/*.py  (copied from core/scripts)

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


ENV_SAMPLE = """\
# RavMem stack settings, read by docker-compose.yml. Do not commit this file.
# Replace each placeholder value below yourself; nothing here is generated for you.

# Password for the ArcadeDB graph database. Use a long random string.
ARCADEDB_PASSWORD=CHANGE_ME

# Admin token for the RavMem server. Choose your own value, e.g. rv_admin_<random>.
# You will give the same value to the RavMem CLI and to the plugin.
RAVMEM_ADMIN_TOKEN=CHANGE_ME

# Optional: change if these ports are taken on your machine.
RAVMEM_PORT=7432
RAVMEM_UI_PORT=3000

# Optional. Leave blank. `ravmem license activate` asks for your license key in the terminal and keeps it on the
# server's data volume, and `ravmem license repair` asks for it again only if it is missing there. Put the key here
# only if you want the server to have it from the start (for example after recreating the data volume).
# It is stored in plain text in this file, so keep the file private and out of git.
RAVMEM_LICENSE_KEY=

# License server used by `ravmem license activate`. Leave as is unless support told you otherwise.
RAVMEM_LICENSE_SERVER_URL=https://console.ravmem.com
"""

COMPOSE_URL = "https://ravmem.com/docs/docker-compose.yml"
ENV_URL = "https://ravmem.com/docs/env.example"

ANTIGRAVITY_PLUGIN_JSON = """\
{
  "$schema": "https://antigravity.google/schemas/v1/plugin.json",
  "name": "ravmem",
  "description": "Code-graph search, impact analysis and shared agent memory for your repos, backed by a self-hosted RavMem server over MCP. Run /ravmem-setup to install a server and /ravmem-configure to connect."
}
"""

SETUP_DESCRIPTION = "Set up RavMem: write the Docker Compose stack and a sample .env, start it, and activate the license with the RavMem CLI"
CONFIGURE_DESCRIPTION = "Point this tool at your RavMem server: set the server URL and the admin token"

SETUP_BODY = """\
Help the user get a RavMem server running. Go through these steps in order, one at a time, and ask before each
action that changes something.

**Secrets stay with the user.** Never ask the user to paste a license key, admin token or password into the chat,
never read or print the `.env` file once it exists, and never run `docker compose down -v` (it deletes all data).

1. **New or existing?** Ask: "Do you already have a RavMem server running, or do you want a new install?"
   If it is already running, skip to step 6.
2. **Docker.** Run `docker compose version` and `docker info`. If either fails, tell the user to install or start
   Docker (https://docs.docker.com/get-docker/) and stop.
3. **Who does it, and where?** Ask whether they want you to set it up for them, or to do it themselves while you
   write the files and print the commands. Ask which folder to use (default: the current directory; create any
   other path they give). If `docker-compose.yml` or `.env` already exists there, ask before touching it.
4. **Write the files.**
   - Compose file, always downloaded fresh, never from memory or an older copy:
     `curl -fsSL -H "Cache-Control: no-cache" -o <folder>/docker-compose.yml {compose_url}`
     If the download fails, stop and say so. Show the user the images it uses (`grep image: <folder>/docker-compose.yml`).
   - Sample env file, only if there is no `.env` yet: `curl -fsSL -o <folder>/.env {env_url}` then `chmod 600 <folder>/.env`.
     If that URL returns 404, write this text to `<folder>/.env` instead:

```
{env_sample}```

   - Tell the user to open `<folder>/.env` themselves and replace each `CHANGE_ME` (database password, an admin
     token of their choice, and the ports if they changed them). Wait until they say it is done, then check
     with `grep -c '=CHANGE_ME' <folder>/.env` (it prints only a count). It must be 0. `RAVMEM_LICENSE_KEY` is optional and may stay blank; never ask the user to tell you the key. Remind them to keep the
     admin token: they need it in steps 6 and 7.
5. **Start the stack.** First check for clashes: `docker ps -a --format '{{{{.Names}}}}'` must not list `ravmem`, `arcadedb`
   or `ravmem-ui`, and the ports in `.env` must be free.
   - **Always pull first.** `up -d` reuses any image already on the machine, and `latest` is not refreshed
     automatically, so an old copy would start. Run `docker compose --project-directory <folder> pull`
     (it downloads the current `ravmem`, `ravmem-ui` and `arcadedb` images), then start.
   - If you do it for them: `docker compose --project-directory <folder> pull`, then
     `docker compose --project-directory <folder> up -d`, then wait for `curl -s http://localhost:<port>/health` to
     answer (the first start can take a few minutes).
   - If they do it: print `cd <folder> && docker compose pull && docker compose up -d` and wait for them to confirm.
6. **Activate the license** (the user does this in a normal terminal; the key and token are typed there and
   never shown to you). The RavMem CLI is the supported way to activate:
   ```
   pip install ravmem-cli            # or: pipx install ravmem-cli, skip if `ravmem --version` works
   ravmem remote config --url http://localhost:<port>
   ravmem remote config --api-key <the admin token you put in .env>
   ravmem license activate           # prompts for the license key (hidden)
   ravmem license status             # should show ACTIVE
   ```
   Use their real port if it is not 7432. If they have not got a license key yet, point them to the RavMem console.
7. **Connect this tool.** Tell the user to run {configure_cmd} to set the server URL and admin token, then
   restart {tool}.
"""

CONFIGURE_BODY = """\
Connect {tool} to the RavMem server the user has running. You never see the admin token: the user enters it.

1. Ask for the server URL, or use the default `http://localhost:7432`. Check it is up with
   `curl -s <url>/health`; if that fails, tell them to finish `{setup_cmd}` first.
2. {how}
3. Restart {tool}, then verify: {verify}
4. If the connection is refused with 401, the token does not match `RAVMEM_ADMIN_TOKEN` in their `.env`;
   they should re-enter it. Do not read the `.env` for them.
"""

CONFIGURE_HOW = {
    "claude-code": "Ask the user to open `/plugin`, select **ravmem**, and edit its options: **server_url** (only if it is not "
                   "the default) and **token** (the admin token they chose in `.env`). The token field is hidden and stored "
                   "securely; do not ask them to type it into the chat.",
    "cursor": "If the URL is not the default, run `python3 .cursor/scripts/install_to_project.py --server-url <url> --force` "
              "to rewrite `.cursor/mcp.json`. The token is read from the `RAVMEM_TOKEN` environment variable: ask the user to set it "
              "to their admin token in the shell or profile that launches Cursor.",
    "codex": "If the URL is not the default, ask the user to edit `url` under `[mcp_servers.ravmem]` in `~/.codex/config.toml` "
             "(or the project's `.codex/config.toml`). The token is read from the `RAVMEM_TOKEN` environment variable: ask the user "
             "to export it with their admin token before starting Codex.",
    "antigravity": "The MCP connection is not part of the plugin, so the token survives plugin updates. Ask the user to add this "
                   "entry to their own **global** `~/.gemini/config/mcp_config.json` (create the file if it does not exist, and merge "
                   "into any existing `mcpServers`), replacing `YOUR_RAVMEM_TOKEN` with their admin token themselves. Use their "
                   "URL if it is not the default, and keep the file private.\n"
                   "   ```json\n"
                   "   {\"mcpServers\": {\"ravmem\": {\n"
                   "     \"serverUrl\": \"http://localhost:7432/mcp\",\n"
                   "     \"headers\": {\"Authorization\": \"Bearer YOUR_RAVMEM_TOKEN\", \"X-KG-Team\": \"default\", \"X-KG-Branch\": \"global\"}\n"
                   "   }}}\n"
                   "   ```",
}

HARNESS = {
    "claude-code": {"tool": "Claude Code", "setup": "`/ravmem:ravmem-setup`", "configure": "`/ravmem:ravmem-configure`",
                    "verify": "ask the user to run `/mcp` (ravmem should be connected with 18 tools), then call the `projects_list` tool yourself."},
    "cursor": {"tool": "Cursor", "setup": "`/ravmem-setup`", "configure": "`/ravmem-configure`",
               "verify": "call the `projects_list` tool yourself and report whether it answers."},
    "codex": {"tool": "Codex", "setup": "`/prompts:ravmem-setup`", "configure": "`/prompts:ravmem-configure`",
              "verify": "call the `projects_list` tool yourself and report whether it answers."},
    "antigravity": {"tool": "Antigravity", "setup": "the `ravmem-setup` skill", "configure": "the `ravmem-configure` skill",
                    "verify": "call the `projects_list` tool yourself and report whether it answers."},
}


# Claude Desktop cannot run commands, so its skills guide the user to run each step in their own terminal.
DESKTOP_SETUP_BODY = """\
Help the user get a RavMem server running. Claude Desktop cannot run commands, so you explain each step and the user
runs the commands in a terminal. Go one step at a time.

**Secrets stay with the user.** Never ask them to paste a license key, admin token or password into this chat, and
never ask them to show you their `.env`.

1. **New or existing?** Ask: "Do you already have a RavMem server running, or do you want a new install?" If it is
   already running, go to step 6.
2. **Docker.** Ask them to run `docker compose version` and `docker info`. If either fails, point them to
   https://docs.docker.com/get-docker/ and stop.
3. **Where?** Ask which folder to use (a new empty folder is best).
4. **Files.** Give them these commands (macOS/Linux; on Windows PowerShell use `Invoke-WebRequest -Uri <url> -OutFile <file>`
   instead of `curl`, and skip `chmod`):
   ```
   mkdir -p <folder> && cd <folder>
   curl -fsSL -H "Cache-Control: no-cache" -o docker-compose.yml {compose_url}
   curl -fsSL -o .env {env_url} && chmod 600 .env
   ```
   If the second download returns 404, give them this text to save as `.env` instead:

```
{env_sample}```

   Tell them to open `.env` themselves and replace each `CHANGE_ME` (a long random database password and an admin
   token of their choice, plus the ports if they changed them). `RAVMEM_LICENSE_KEY` is optional and may stay blank.
   They must keep the admin token: they need it in steps 6 and 7.
5. **Start the stack.** `docker compose pull` first (it fetches the current images; `up` alone reuses an old cached
   `latest`), then `docker compose up -d`. Then `curl -s http://localhost:7432/health` should answer (use their port).
   If `ravmem`, `arcadedb` or `ravmem-ui` containers already exist from another install, have them resolve that first.
6. **Activate the license** in a terminal (the key and token are typed there, never into this chat):
   ```
   pip install ravmem-cli            # or: pipx install ravmem-cli, skip if `ravmem --version` works
   ravmem remote config --url http://localhost:7432
   ravmem remote config --api-key <the admin token from .env>
   ravmem license activate           # prompts for the license key (hidden)
   ravmem license status             # should show ACTIVE
   ```
7. **Connect Claude Desktop** with the `ravmem-configure` skill.
"""

DESKTOP_CONFIGURE_BODY = """\
Connect Claude Desktop to the RavMem server the user has running. You cannot run commands or see the admin token.

1. Ask them to confirm the server is up and activated: `curl -s http://localhost:7432/health` and `ravmem license status`
   (ACTIVE). If not, go back to the `ravmem-setup` skill.
2. In the folder where they cloned this repository, ask them to run:
   ```
   python3 claude-desktop/scripts/install_config.py          # add --force to replace an existing ravmem entry
   ```
   It reads the server URL and admin token from `~/.ravmem/client.json`, which `ravmem remote config` already wrote, adds the
   `ravmem` entry to `claude_desktop_config.json` (using the standard `mcp-remote` package, so Node.js is required), makes a
   backup first and checks the server answers. The token goes into that file's `env` block (mode 600); it never appears here.
3. Ask them to fully quit and reopen Claude Desktop. Then the `ravmem` tools should be listed; ask them to try
   "list my RavMem projects".
4. If the server answers 401, the token in `~/.ravmem/client.json` does not match `RAVMEM_ADMIN_TOKEN` in their `.env`:
   re-run `ravmem remote config --api-key <token>` and then `install_config.py --force`.
"""


def setup_body(harness: str) -> str:
    if harness == "claude-desktop":
        return DESKTOP_SETUP_BODY.format(compose_url=COMPOSE_URL, env_url=ENV_URL, env_sample=ENV_SAMPLE)
    h = HARNESS[harness]
    return SETUP_BODY.format(compose_url=COMPOSE_URL, env_url=ENV_URL, env_sample=ENV_SAMPLE,
                             configure_cmd=h["configure"], tool=h["tool"])


def configure_body(harness: str) -> str:
    if harness == "claude-desktop":
        return DESKTOP_CONFIGURE_BODY
    h = HARNESS[harness]
    return CONFIGURE_BODY.format(tool=h["tool"], setup_cmd=h["setup"].strip("`"), how=CONFIGURE_HOW[harness], verify=h["verify"])


def _command(description: str, body: str, tools: str = "") -> str:
    extra = f"allowed-tools: {tools}\n" if tools else ""
    return f"---\ndescription: {description}\n{extra}disable-model-invocation: true\n---\n\n{body}"


def _plain(title: str, body: str) -> str:
    return f"# {title}\n\n{body}"


def _skill(name: str, description: str, body: str) -> str:
    return f"---\nname: {name}\ndescription: {description}. User-invoked only.\ndisable-model-invocation: true\n---\n\n{body}"


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


def instructions_block(harness: str, config_key: str, setup_key: str) -> str:
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
    h = HARNESS[setup_key]
    parts += [
        "### 6. Installing and connecting the RavMem server",
        "",
        f"If the user wants a RavMem server installed, follow {h['setup']}: write the Docker Compose file (downloaded fresh from "
        f"{COMPOSE_URL}) and a sample `.env`, start the stack, and have the user activate the license with `ravmem license "
        "activate` in their own terminal. Never ask for, read or print the license key, admin token or `.env`. "
        f"To connect {h['tool']} to a running server, follow {h['configure']}.",
        "",
    ]
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

    for name, desc, body_fn, tools in (("ravmem-setup", SETUP_DESCRIPTION, setup_body, "Bash(docker:*), Bash(curl:*), Bash(chmod:*), Bash(grep:*)"),
                                       ("ravmem-configure", CONFIGURE_DESCRIPTION, configure_body, "Bash(curl:*)")):
        title = "Set up the RavMem server" if name == "ravmem-setup" else "Connect to your RavMem server"
        out[ROOT / "claude-code" / "commands" / f"{name}.md"] = _command(desc, body_fn("claude-code"), tools)
        out[ROOT / "cursor" / "commands" / f"{name}.md"] = _plain(title, body_fn("cursor"))
        out[ROOT / "codex" / "prompts" / f"{name}.md"] = _plain(title, body_fn("codex"))
        out[ROOT / "antigravity" / "skills" / name / "SKILL.md"] = _skill(name, desc, body_fn("antigravity"))
        out[ROOT / "claude-desktop" / "skills" / name / "SKILL.md"] = _skill(name, desc, body_fn("claude-desktop"))

    # Antigravity plugin = the repo root: plugin.json + skills/ + rules/ (agy prefers plugin.json over .claude-plugin).
    # Skills + rules only. The MCP connection is deliberately left out so the user's token
    # lives in their own mcp_config.json and survives plugin updates (see /ravmem-configure).
    out[ROOT / "plugin.json"] = ANTIGRAVITY_PLUGIN_JSON
    for path, content in list(out.items()):
        parts = path.relative_to(ROOT).parts
        if parts[0] == "antigravity" and parts[1] in ("skills", "rules"):
            out[ROOT / Path(*parts[1:])] = content

    for src in sorted((ROOT / "core" / "scripts").glob("*.py")):
        for harness in ("claude-code", "claude-desktop", "antigravity", "cursor", "codex"):
            out[ROOT / harness / "scripts" / src.name] = src.read_text(encoding="utf-8")

    codex_block = instructions_block("project", "mcp_servers", "codex")
    ag_block = instructions_block("workspace", "mcpServers", "antigravity")
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
