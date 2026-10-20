---
name: ravmem-configure
description: Point this tool at your RavMem server: set the server URL and the admin token. User-invoked only.
disable-model-invocation: true
---

Connect Claude Desktop to the RavMem server the user has running. You cannot run commands or see the admin token.

1. Ask them to confirm the server is up and activated: `curl -s http://localhost:7432/health` and `ravmem license status`
   (ACTIVE). If not, go back to the `ravmem-setup` skill.
2. In the folder where they cloned this repository, ask them to run:
   ```
   python3 claude-desktop/scripts/install_config.py          # add --force to replace an existing ravmem entry
   ```
   It reads the server URL and admin token from `~/.ravmem/client.json`, which `ravmem remote config` already wrote, adds the
   `ravmem` entry to `claude_desktop_config.json` (using the standard `mcp-remote` package, so Node.js is required), makes a
   backup first and checks the server answers. The token goes into that file's `env` block (mode 600); it never appears here.
3. Ask them to fully quit and reopen Claude Desktop. Then the `ravmem` tools should be listed; ask them to try
   "list my RavMem projects".
4. If the server answers 401, the token in `~/.ravmem/client.json` does not match `RAVMEM_ADMIN_TOKEN` in their `.env`:
   re-run `ravmem remote config --api-key <token>` and then `install_config.py --force`.
