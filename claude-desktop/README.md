# RavMem for Claude Desktop

```
python3 claude-desktop/scripts/install_config.py
```

Claude Desktop launches only local servers from `claude_desktop_config.json`, so the entry runs the standard
[`mcp-remote`](https://www.npmjs.com/package/mcp-remote) package through `npx` (Node.js required); it forwards to
`<server>/mcp` with your bearer token. The token is stored in the entry's `env` block of your user config file
(mode 600). A backup of the existing config is written first. Restart Claude Desktop afterwards.

The `skills/` folder holds the same five skills as the Claude Code plugin, for use wherever your Claude Desktop setup loads skills.

## Install the server

Claude Desktop has no commands or shell, so follow the "Installing the server" steps in the repository README by hand (download the compose file, fill in `.env`, `docker compose up -d`, `ravmem license activate`), then run `install_config.py`.
