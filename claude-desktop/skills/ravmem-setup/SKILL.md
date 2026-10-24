---
name: ravmem-setup
description: Set up RavMem: write the Docker Compose stack and a sample .env, start it, and activate the license with the RavMem CLI. User-invoked only.
disable-model-invocation: true
---

Help the user get a RavMem server running. Claude Desktop cannot run commands, so you explain each step and the user
runs the commands in a terminal. Go one step at a time.

**Secrets stay with the user.** Never ask them to paste a license key, admin token or password into this chat, and
never ask them to show you their `.env`.

1. **New or existing?** Ask: "Do you already have a RavMem server running, or do you want a new install?" If it is
   already running, go to step 6.
2. **Docker.** Ask them to run `docker compose version` and `docker info`. If either fails, point them to
   https://docs.docker.com/get-docker/ and stop.
3. **Where?** Ask which folder to use (a new empty folder is best).
4. **Files.** Give them these commands (macOS/Linux; on Windows PowerShell use `Invoke-WebRequest -Uri <url> -OutFile <file>`
   instead of `curl`, and skip `chmod`):
   ```
   mkdir -p <folder> && cd <folder>
   curl -fsSL -H "Cache-Control: no-cache" -o docker-compose.yml https://ravmem.com/docs/docker-compose.yml
   curl -fsSL -o .env https://ravmem.com/docs/env.example && chmod 600 .env
   ```
   If the second download returns 404, give them this text to save as `.env` instead:

```
# RavMem stack settings, read by docker-compose.yml. Do not commit this file.
# Replace each placeholder value below yourself; nothing here is generated for you.

# Password for the ArcadeDB graph database. Use a long random string.
ARCADEDB_PASSWORD=CHANGE_ME

# Admin token for the RavMem server. Choose your own value, e.g. rv_admin_<random>.
# You will give the same value to the RavMem CLI and to the plugin.
RAVMEM_ADMIN_TOKEN=CHANGE_ME

# Optional: change if these ports are taken on your machine.
RAVMEM_PORT=7432
RAVMEM_UI_PORT=3000

# Your RavMem license key (provided at purchase). Replace CHANGE_ME with it. `ravmem license activate` also asks for the
# key in the terminal, and `ravmem license repair` uses the value here to re-fetch your license without asking again.
# It is stored in plain text in this file, so keep the file private and out of git.
RAVMEM_LICENSE_KEY=CHANGE_ME

# License server used by `ravmem license activate`. Leave as is unless support told you otherwise.
RAVMEM_LICENSE_SERVER_URL=https://console.ravmem.com
```

   Tell them to open `.env` themselves and replace each `CHANGE_ME` (a long random database password and an admin
   token of their choice, their license key in `RAVMEM_LICENSE_KEY`, plus the ports if they changed them). Never ask them to tell you the key.
   They must keep the admin token: they need it in steps 6 and 7.
5. **Start the stack.** `docker compose pull` first (it fetches the current images; `up` alone reuses an old cached
   `latest`), then `docker compose up -d`. Then `curl -s http://localhost:7432/health` should answer (use their port).
   If `ravmem`, `arcadedb` or `ravmem-ui` containers already exist from another install, have them resolve that first.
6. **Activate the license** in a terminal (the key and token are typed there, never into this chat):
   ```
   pip install ravmem-cli            # or: pipx install ravmem-cli, skip if `ravmem --version` works
   ravmem remote config --url http://localhost:7432
   ravmem remote config --api-key <the admin token from .env>
   ravmem license activate           # prompts for the license key (hidden)
   ravmem license status             # should show ACTIVE
   ```
7. **Connect Claude Desktop** with the `ravmem-configure` skill.
