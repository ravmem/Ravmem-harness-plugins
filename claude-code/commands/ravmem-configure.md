---
description: Point this tool at your RavMem server: set the server URL and the admin token
allowed-tools: Bash(curl:*)
disable-model-invocation: true
---

Connect Claude Code to the RavMem server the user has running. You never see the admin token: the user enters it.

1. Ask for the server URL, or use the default `http://localhost:7432`. Check it is up with
   `curl -s <url>/health`; if that fails, tell them to finish `/ravmem:ravmem-setup` first.
2. Ask the user to open `/plugin`, select **ravmem**, and edit its options: **server_url** (only if it is not the default) and **token** (the admin token they chose in `.env`). The token field is hidden and stored securely; do not ask them to type it into the chat.
3. Restart Claude Code, then verify: ask the user to run `/mcp` (ravmem should be connected with 18 tools), then call the `projects_list` tool yourself.
4. If the connection is refused with 401, the token does not match `RAVMEM_ADMIN_TOKEN` in their `.env`;
   they should re-enter it. Do not read the `.env` for them.
