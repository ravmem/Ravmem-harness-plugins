# RavMem for Claude Desktop

```
python3 claude-desktop/scripts/install_config.py
```

Claude Desktop launches only local servers from `claude_desktop_config.json`, so the entry runs the standard
[`mcp-remote`](https://www.npmjs.com/package/mcp-remote) package through `npx` (Node.js required); it forwards to
`<server>/mcp` with your bearer token. The token is stored in the entry's `env` block of your user config file
(mode 600). A backup of the existing config is written first. Restart Claude Desktop afterwards.

The `skills/` folder holds the same five skills as the Claude Code plugin, for use wherever your Claude Desktop setup loads skills.
