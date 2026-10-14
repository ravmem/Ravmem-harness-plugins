# Set up the RavMem server

Set up the RavMem server on this machine. The installer downloads the **latest** Docker Compose file from
https://ravmem.com/docs/docker-compose.yml (never a bundled copy), starts the stack, activates the license and
writes `~/.ravmem/client.json` so this tool and the RavMem CLI can connect.

**The license key must never pass through this chat.** Do not ask the user to paste it and do not run the
installer yourself: it needs a real terminal to read the key without echo.

1. Check Docker is usable: `docker compose version` and `docker info`. If either fails, tell the user to install
   or start Docker (https://docs.docker.com/get-docker/) and stop.
2. Ask the user to run `python3 .cursor/scripts/setup_stack.py` in Cursor's integrated terminal. They need their RavMem license key (it starts with `RAVMEM-`). Add `--port <n>`
   or `--ui-port <n>` for non-default ports. In a shell without a terminal prompt they can export `RAVMEM_LICENSE_KEY`
   first instead.
3. The installer also offers to install the RavMem CLI (`ravmem-cli`), which is needed to index a repository.
   Afterwards run the same script with `status` and report the result.
4. The server URL and admin token are now in `~/.ravmem/client.json` (the token is also in `~/.ravmem/stack/.env`).
   Run `python3 .cursor/scripts/install_to_project.py --force`, export `RAVMEM_TOKEN` with the admin token, and restart Cursor.

If the installer reports an error, show it as is and suggest the fix it names. Never run `docker compose down -v`
(it deletes all RavMem data) and never print the admin token or license key.
