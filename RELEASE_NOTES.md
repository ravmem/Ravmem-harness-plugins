# Release notes

## 0.2.0 — Standard MCP, no local bridge

Requires a RavMem server with the MCP revamp (the `/mcp` endpoint with 18 tools, 6 resource templates and
5 prompts). Older servers expose a different, non-standard `/mcp` and will not work with this release.

### Breaking changes

- **The stdio bridge is gone.** Every harness connects directly to `<server>/mcp` (Streamable HTTP, bearer
  token). Remove any config that launches `ravmem-mcp-bridge`, and drop the `backend` and `cli_path` options.
  Re-run your harness's installer, or reinstall the Claude Code plugin, to get the new connection.
- **New tool names.** The previous tools (`search_symbols`, `get_symbol`, `get_impact`, `diff_impact`,
  `get_call_chain`, `list_nodes`, `load_task_context`, `log_decision`, `log_learning`, and the rest) no
  longer exist. They are replaced by `projects_list`, `code_search`, `code_get_symbol`, `code_relations`,
  `code_explore`, `code_impact`, `code_call_chain`, `project_sync`, `jobs`, and the `memory_*` tools.
  Skills and rules are updated; any saved prompts or `allowed-tools` lists of your own need updating.
- **Session-transfer tokens removed.** `ravmem_session_transfer` and `ravmem_session_resume`, and the local
  `~/.ravmem/session_transfers.db`, are gone. Hand a session to another tool by recording the task, decisions,
  blockers and a context note in memory (the server's `session_handoff` prompt does this); the next tool loads
  them with `memory_list` and `memory_load_context`.
- **`ravmem_onboard_repo` removed.** An MCP server cannot read your disk. Index a repository with
  `ravmem remote add . --name <project>` then `ravmem analyze . --project <project> --wait` (from
  `pip install ravmem-cli`); `project_sync` then keeps server-cloned projects current and
  `ravmem analyze . --project <project> --incremental` updates uploaded ones.
- **Claude Desktop `.dxt` bundle removed.** It packaged the bridge. Claude Desktop is now configured through
  `claude_desktop_config.json` using the standard `mcp-remote` package (needs Node.js).

### Added

- Claude Code plugin 0.2.0: `type: http` connection; options `server_url`, `token`, `kg_team`, `kg_branch`.
- Memory scope is explicit: every config sends `X-KG-Team` (default `default`) and `X-KG-Branch`
  (default `global`).
- `build_content.py` generates all skills, rules and `AGENTS.md` / `GEMINI.md` blocks from one source;
  `--check` fails if any file is out of date.
- Installers for Cursor, Codex, Antigravity and Claude Desktop that discover the server and token from flags,
  `RAVMEM_SERVER_URL` / `RAVMEM_TOKEN`, then `~/.ravmem/client.json`, and check that the server answers.
- Cursor install link generator that carries no secret by default.
- **Guided server setup**: `/ravmem:ravmem-setup` (Claude Code), a Cursor command, a Codex prompt and an Antigravity
  skill walk you through a new install: ask new or existing, who does the work and where, then download the latest
  compose file from `https://ravmem.com/docs/docker-compose.yml` and write a sample `.env` (`CHANGE_ME` placeholders you
  fill in yourself), start the stack, and have you activate the license with `ravmem license activate` in your own
  terminal. The assistant never reads the `.env` and never sees the license key or admin token (`RAVMEM_LICENSE_KEY` in the sample `.env` is optional and left blank).
  `/ravmem:ravmem-configure` (and equivalents) then connect the tool to the server.
- Installing the Claude Code plugin no longer requires `server_url` or `token`: leave them blank on the options screen and set
  them afterwards with `/ravmem:ravmem-configure` (the option descriptions say so).

### Changed

- Session hooks (`check_onboarding.py`, `load_kg_context.py`) and `prune_kg.py` are standard-library REST
  scripts. `check_onboarding.py` now asks the server whether a project exists instead of keeping a local
  marker file. All exit quietly if the server is unreachable.
- Tokens are not written into project files: Cursor and Codex read `RAVMEM_TOKEN`; Antigravity project mode
  leaves a placeholder (use `--global` for a private config).

### Verified against the new server image

Tested against `ampaulravmem/ravmem:mcp-revamp` (encrypted, amd64) running in the docker-compose stack: 127 of
128 MCP checks passed on the first build, covering the protocol (three protocol versions, auth, malformed
input), all 18 tools with happy and error paths, 6 resources, 5 prompts, memory isolation between teams, and
the plan's connection limit. The one failure, `from package import module` imports not appearing in
`code_relations`, and four behaviors the guidance had to work around are fixed in the next server build;
this release's guidance assumes that build:

- `memory_load_context(task_id)` includes the task's own learnings and decisions.
- `memory_list` hides completed tasks unless `include_completed` is true.
- `code_relations` resolves `from package import module`, `from . import module` and parenthesised imports
  (re-index a project to pick this up). Plain `import x` and imports inside functions are still not tracked.
- A request refused for the plan's concurrent-connection limit (5 on the beta plan) returns HTTP 429 with
  `Retry-After` and a JSON-RPC error body.

Also worth knowing: the code tools use the project's default branch; if it differs from the indexed branch they
answer with the list of available branches.

### Known limitations

- Verified: installers and hook scripts against throwaway directories and a live server's REST API.
  Not yet verified: a harness connecting to `/mcp` on a server running the new image; Claude Code passing
  plugin options to hooks as `CLAUDE_PLUGIN_OPTION_*`; Antigravity header handling and Cursor `${env:...}`
  expansion in real clients.
- Antigravity's MCP config cannot read environment variables.
