# RavMem for Cursor

```
python3 cursor/scripts/install_to_project.py /path/to/project
export RAVMEM_TOKEN=<token>      # in the environment Cursor is started from
```

Writes `.cursor/mcp.json` (URL + `Authorization: Bearer ${env:RAVMEM_TOKEN}`, so it is safe to commit), copies the
five rules to `.cursor/rules/`, and the maintenance scripts to `.cursor/scripts/`. Server and token are discovered
from `--server-url`, `RAVMEM_SERVER_URL` / `RAVMEM_TOKEN`, then `~/.ravmem/client.json`.

One-click alternative: `python3 cursor/scripts/generate_deeplink.py` prints a `cursor://` install link that also
reads the token from `RAVMEM_TOKEN`.

## Install the server

`/ravmem-setup` (in `.cursor/commands/`) guides you through writing the compose file and a sample `.env`, starting the stack and activating the license with the RavMem CLI. Afterwards `/ravmem-configure` connects Cursor to it. See the repository README, "Installing the server".
