---
name: ravmem-configure
description: Point this tool at your RavMem server: set the server URL and the admin token. User-invoked only.
disable-model-invocation: true
---

Connect Antigravity to the RavMem server the user has running. You never see the admin token: the user enters it.

1. Ask for the server URL, or use the default `http://localhost:7432`. Check it is up with
   `curl -s <url>/health`; if that fails, tell them to finish `the `ravmem-setup` skill` first.
2. The MCP connection is not part of the plugin, so the token survives plugin updates. Ask the user to add this entry to their own **global** `~/.gemini/config/mcp_config.json` (create the file if it does not exist, and merge into any existing `mcpServers`; if there is an old `ravmem` entry with a `command` (the removed local bridge), replace it), replacing `YOUR_RAVMEM_TOKEN` with their admin token themselves. Use their URL if it is not the default, and keep the file private.
   ```json
   {"mcpServers": {"ravmem": {
     "serverUrl": "http://localhost:7432/mcp",
     "headers": {"Authorization": "Bearer YOUR_RAVMEM_TOKEN", "X-KG-Team": "default", "X-KG-Branch": "global"}
   }}}
   ```
3. Restart Antigravity, then verify: call the `projects_list` tool yourself and report whether it answers.
4. If the connection is refused with 401, the token does not match `RAVMEM_ADMIN_TOKEN` in their `.env`;
   they should re-enter it. Do not read the `.env` for them.
