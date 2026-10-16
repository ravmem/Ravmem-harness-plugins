# Connect to your RavMem server

Connect Codex to the RavMem server the user has running. You never see the admin token: the user enters it.

1. Ask for the server URL, or use the default `http://localhost:7432`. Check it is up with
   `curl -s <url>/health`; if that fails, tell them to finish `/prompts:ravmem-setup` first.
2. If the URL is not the default, ask the user to edit `url` under `[mcp_servers.ravmem]` in `~/.codex/config.toml` (or the project's `.codex/config.toml`). The token is read from the `RAVMEM_TOKEN` environment variable: ask the user to export it with their admin token before starting Codex.
3. Restart Codex, then verify: call the `projects_list` tool yourself and report whether it answers.
4. If the connection is refused with 401, the token does not match `RAVMEM_ADMIN_TOKEN` in their `.env`;
   they should re-enter it. Do not read the `.env` for them.
