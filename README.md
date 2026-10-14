# RavMem harness plugins

Integrations that connect AI coding tools to a self-hosted [RavMem](https://github.com/ravmem) server: code-graph
search, impact analysis, and shared agent memory.

Every integration talks to the server's **standard MCP endpoint** — `http://<server>:7432/mcp`, Streamable HTTP,
bearer-token auth. There is no local adapter or proxy to install (Claude Desktop is the one exception, see below).
What each plugin adds is the harness-specific wiring: the connection config, the guidance that tells the model
when to use which tool, and optional session hooks.

| Harness | What you get | Install |
|---|---|---|
| [Claude Code](claude-code/README.md) | Plugin: MCP connection, 5 skills, SessionStart hooks | `/plugin marketplace add` this repo, then `/plugin install ravmem@ravmem-integrations` |
| [Cursor](cursor/README.md) | `.cursor/mcp.json`, 5 rules | `python3 cursor/scripts/install_to_project.py` |
| [Codex CLI](codex/README.md) | `config.toml` entry, `AGENTS.md` rules | `python3 codex/scripts/install_to_project.py` |
| [Antigravity](antigravity/README.md) | `mcp_config.json`, rules, skills, `GEMINI.md` | `python3 antigravity/scripts/install_to_project.py` |
| [Claude Desktop](claude-desktop/README.md) | `claude_desktop_config.json` entry (via `mcp-remote`), skills | `python3 claude-desktop/scripts/install_config.py` |

## What the model can use

The server exposes 18 tools, 6 resource templates and 5 prompts (`GET <server>/api/mcp/tools` lists the tools).

- **Code graph** — `projects_list`, `code_search`, `code_get_symbol`, `code_relations`, `code_explore`,
  `code_impact`, `code_call_chain`
- **Index operations** — `project_sync`, `jobs`
- **Memory** — `memory_load_context`, `memory_search`, `memory_get`, `memory_list`, `memory_task`,
  `memory_record`, `memory_link_code`, `memory_review`, `memory_update`
- **Prompts** — `session_start`, `pre_edit_impact`, `onboard_repo`, `session_handoff`, `review_learnings`

## Requirements

- A RavMem server running the MCP revamp (the `/mcp` endpoint with the tools above). Older servers expose a
  different, non-standard `/mcp` and will not work with these plugins.
- A token. The admin token is printed once at server start; for day-to-day use create a user token with
  `ravmem auth create-token`. Reading needs `repo:read`, `branch:read`, `job:read`, `kg:read`; recording memory
  needs `kg:write`; `project_sync` needs `branch:index`; validating and promoting learnings needs `kg:validate`.
- To index a repository from your machine: `pip install ravmem-cli`, then `ravmem remote add . --name <project>` and
  `ravmem analyze . --project <project> --wait`.
  An MCP server cannot read your disk, so the first upload is a CLI step; afterwards `project_sync` keeps
  server-cloned projects fresh and `ravmem analyze . --project <project> --incremental` updates uploaded ones.

## Installing the server

No server yet? `scripts/setup_stack.py` (shipped in every plugin, standard library only) installs and activates one
with Docker. It downloads the **latest** Docker Compose file from `https://ravmem.com/docs/docker-compose.yml` on every
run (nothing is bundled or reused), generates the admin token and database password into `~/.ravmem/stack/.env`,
starts the stack, activates your license, and writes `~/.ravmem/client.json` so the other installers and the CLI find
the server. You type the license key into the terminal (hidden) or export `RAVMEM_LICENSE_KEY`; it is never taken as
an argument, written to disk or printed.

| Harness | How to run it |
|---|---|
| Claude Code | `/ravmem:ravmem-setup`, then type `! python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup_stack.py"` when it asks |
| Cursor | `/ravmem-setup` command, or `python3 .cursor/scripts/setup_stack.py` |
| Codex CLI | `/prompts:ravmem-setup` (after `install_to_project.py --global`), or `python3 ~/.codex/scripts/setup_stack.py` |
| Antigravity | the `ravmem-setup` skill, or `python3 .agents/scripts/setup_stack.py` |
| Claude Desktop | no shell access: run `python3 claude-desktop/scripts/setup_stack.py` yourself in a terminal |

It needs Docker with Compose v2 and a running daemon, Python 3.8+, and a RavMem license key. Re-running it is safe: it
refreshes the compose file, keeps your secrets and data, and skips activation when the license is already active. Use
`--port` / `--ui-port` to avoid busy ports, `--compose-url` (or `RAVMEM_COMPOSE_URL`) to test against another file, and
`status` to check the stack. It refuses to run if containers named `ravmem`, `arcadedb` or `ravmem-ui` already exist
from another stack. Tests: `python3 -m unittest tests.test_setup_stack`.

## Memory scope

Memory is shared per team and knowledge branch. Each config sends `X-KG-Team` (default `default`) and
`X-KG-Branch` (default `global`) headers; change them in the config to use another scope. The model never
chooses the scope.

## Session handoff between tools

There are no transfer tokens. Record the task, decisions, blockers and a context note in memory before stopping
(the `session_handoff` prompt does this); the next tool starts from `memory_list` / `memory_load_context`.

## Maintaining the guidance

The skills, rules and `AGENTS.md`/`GEMINI.md` blocks are generated from one source so the harnesses cannot drift:

```
python3 build_content.py           # rewrite generated files
python3 build_content.py --check   # fail if any is out of date (use in CI)
```

Edit `build_content.py` (guidance text) or `core/scripts/` (hook and maintenance scripts), never the generated copies.
The scripts are standard-library Python so they can be copied into projects as-is.
