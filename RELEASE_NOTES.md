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
  `ravmem analyze . --wait` (from `pip install ravmem-cli`); `project_sync` then keeps server-cloned projects
  current and `ravmem analyze . --incremental` updates uploaded ones.
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

### Changed

- Session hooks (`check_onboarding.py`, `load_kg_context.py`) and `prune_kg.py` are standard-library REST
  scripts. `check_onboarding.py` now asks the server whether a project exists instead of keeping a local
  marker file. All exit quietly if the server is unreachable.
- Tokens are not written into project files: Cursor and Codex read `RAVMEM_TOKEN`; Antigravity project mode
  leaves a placeholder (use `--global` for a private config).

### Known limitations

- Verified: installers and hook scripts against throwaway directories and a live server's REST API.
  Not yet verified: a harness connecting to `/mcp` on a server running the new image; Claude Code passing
  plugin options to hooks as `CLAUDE_PLUGIN_OPTION_*`; Antigravity header handling and Cursor `${env:...}`
  expansion in real clients.
- Antigravity's MCP config cannot read environment variables.
