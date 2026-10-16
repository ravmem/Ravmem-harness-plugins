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

No server yet? Run the setup command from your tool; it walks you through a standard Docker Compose install and never
touches your secrets. Installing the Claude Code plugin shows an options screen where nothing is required: leave it blank and save,
then set the server URL and token afterwards with the configure command.

| Harness | Install the server | Connect to it afterwards |
|---|---|---|
| Claude Code | `/ravmem:ravmem-setup` | `/ravmem:ravmem-configure` |
| Cursor | `/ravmem-setup` | `/ravmem-configure` |
| Codex CLI | `/prompts:ravmem-setup` (after `install_to_project.py --global`) | `/prompts:ravmem-configure` |
| Antigravity | the `ravmem-setup` skill | the `ravmem-configure` skill |
| Claude Desktop | follow the steps below by hand | edit `claude_desktop_config.json` (see its README) |

What the setup flow does:

1. Asks whether you already have a server or want a new install, and whether you or your assistant should do the work
   and in which folder.
2. Downloads the **latest** compose file from `https://ravmem.com/docs/docker-compose.yml` (never a bundled copy) and
   writes a sample `.env` with `CHANGE_ME` placeholders for the database password and the admin token. You fill those in
   yourself; the assistant never reads the file.
3. Starts the stack with `docker compose up -d` (or prints the command if you prefer to run it).
4. You activate the license in your own terminal with the RavMem CLI: `pip install ravmem-cli`,
   `ravmem remote config --url <url>`, `ravmem remote config --api-key <admin token>`, `ravmem license activate`.
   Your license key is typed there. `RAVMEM_LICENSE_KEY` in `.env` is optional and normally left blank.
5. `ravmem-configure` then sets the plugin's server URL (default `http://localhost:7432`) and admin token.

It needs Docker with Compose v2 and a RavMem license key.

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
