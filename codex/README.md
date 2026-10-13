# RavMem for Codex CLI

```
python3 codex/scripts/install_to_project.py /path/to/project     # or --global for ~/.codex/config.toml only
export RAVMEM_TOKEN=<token>
```

Adds `[mcp_servers.ravmem]` (`url` + `bearer_token_env_var = "RAVMEM_TOKEN"`) to `.codex/config.toml`, merges the
RavMem block into `AGENTS.md` between `BEGIN/END RAVMEM INSTRUCTIONS` markers, and copies the maintenance scripts
to `.codex/scripts/`. Re-run with `--force` to refresh the block.
