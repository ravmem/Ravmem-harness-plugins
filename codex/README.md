# RavMem for Codex CLI

```
python3 codex/scripts/install_to_project.py /path/to/project     # or --global for ~/.codex/config.toml only
export RAVMEM_TOKEN=<token>
```

Adds `[mcp_servers.ravmem]` (`url` + `bearer_token_env_var = "RAVMEM_TOKEN"`) to `.codex/config.toml`, merges the
RavMem block into `AGENTS.md` between `BEGIN/END RAVMEM INSTRUCTIONS` markers, and copies the maintenance scripts
to `.codex/scripts/`. Re-run with `--force` to refresh the block.

## Install the server

`python3 codex/scripts/install_to_project.py --global` also installs the `/prompts:ravmem-setup` prompt and `setup_stack.py` under `~/.codex/`. The script installs and activates the RavMem server with Docker; run it in a terminal so the license key is typed privately. See the repository README, "Installing the server".
