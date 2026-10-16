---
name: ravmem-configure
description: Point this tool at your RavMem server: set the server URL and the admin token. User-invoked only.
disable-model-invocation: true
---

Connect Antigravity to the RavMem server the user has running. You never see the admin token: the user enters it.

1. Ask for the server URL, or use the default `http://localhost:7432`. Check it is up with
   `curl -s <url>/health`; if that fails, tell them to finish `the `ravmem-setup` skill` first.
2. Ask the user to open `.agents/mcp_config.json` (or `~/.gemini/config/mcp_config.json`) and set the URL (`<url>/mcp`) and replace `YOUR_RAVMEM_TOKEN` with their admin token themselves. Keep that file out of git.
3. Restart Antigravity, then verify: call the `projects_list` tool yourself and report whether it answers.
4. If the connection is refused with 401, the token does not match `RAVMEM_ADMIN_TOKEN` in their `.env`;
   they should re-enter it. Do not read the `.env` for them.
