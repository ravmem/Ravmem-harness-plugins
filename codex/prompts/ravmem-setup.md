# Set up the RavMem server

Help the user get a RavMem server running. Go through these steps in order, one at a time, and ask before each
action that changes something.

**Secrets stay with the user.** Never ask the user to paste a license key, admin token or password into the chat,
never read or print the `.env` file once it exists, and never run `docker compose down -v` (it deletes all data).

1. **New or existing?** Ask: "Do you already have a RavMem server running, or do you want a new install?"
   If it is already running, skip to step 6.
2. **Docker.** Run `docker compose version` and `docker info`. If either fails, tell the user to install or start
   Docker (https://docs.docker.com/get-docker/) and stop.
3. **Who does it, and where?** Ask whether they want you to set it up for them, or to do it themselves while you
   write the files and print the commands. Ask which folder to use (default: the current directory; create any
   other path they give). If `docker-compose.yml` or `.env` already exists there, ask before touching it.
4. **Write the files.**
   - Compose file, always downloaded fresh, never from memory or an older copy:
     `curl -fsSL -H "Cache-Control: no-cache" -o <folder>/docker-compose.yml https://ravmem.com/docs/docker-compose.yml`
     If the download fails, stop and say so. Show the user the images it uses (`grep image: <folder>/docker-compose.yml`).
   - Sample env file, only if there is no `.env` yet: `curl -fsSL -o <folder>/.env https://ravmem.com/docs/env.example` then `chmod 600 <folder>/.env`.
     If that URL returns 404, write this text to `<folder>/.env` instead:

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

   - Tell the user to open `<folder>/.env` themselves and replace each `CHANGE_ME` (database password, an admin
     token of their choice, their license key, and the ports if they changed them). Wait until they say it is done, then check
     with `grep -c '=CHANGE_ME' <folder>/.env` (it prints only a count). It must be 0. Never ask the user to tell you the license key or read it from the file. Remind them to keep the
     admin token: they need it in steps 6 and 7.
5. **Start the stack.** First check for clashes: `docker ps -a --format '{{.Names}}'` must not list `ravmem`, `arcadedb`
   or `ravmem-ui`, and the ports in `.env` must be free.
   - **Always pull first.** `up -d` reuses any image already on the machine, and `latest` is not refreshed
     automatically, so an old copy would start. Run `docker compose --project-directory <folder> pull`
     (it downloads the current `ravmem`, `ravmem-ui` and `arcadedb` images), then start.
   - If you do it for them: `docker compose --project-directory <folder> pull`, then
     `docker compose --project-directory <folder> up -d`, then wait for `curl -s http://localhost:<port>/health` to
     answer (the first start can take a few minutes).
   - If they do it: print `cd <folder> && docker compose pull && docker compose up -d` and wait for them to confirm.
6. **Activate the license** (the user does this in a normal terminal; the key and token are typed there and
   never shown to you). The RavMem CLI is the supported way to activate:
   ```
   pip install ravmem-cli            # or: pipx install ravmem-cli, skip if `ravmem --version` works
   ravmem remote config --url http://localhost:<port>
   ravmem remote config --api-key <the admin token you put in .env>
   ravmem license activate           # prompts for the license key (hidden)
   ravmem license status             # should show ACTIVE
   ```
   Use their real port if it is not 7432. If they have not got a license key yet, point them to the RavMem console.
7. **Connect this tool.** Tell the user to run `/prompts:ravmem-configure` to set the server URL and admin token, then
   restart Codex.
