# Connect to your RavMem server

Connect Cursor to the RavMem server the user has running. You never see the admin token: the user enters it.

1. Ask for the server URL, or use the default `http://localhost:7432`. Check it is up with
   `curl -s <url>/health`; if that fails, tell them to finish `/ravmem-setup` first.
2. If the URL is not the default, run `python3 .cursor/scripts/install_to_project.py --server-url <url> --force` to rewrite `.cursor/mcp.json`. The token is read from the `RAVMEM_TOKEN` environment variable: ask the user to set it to their admin token in the shell or profile that launches Cursor.
3. Restart Cursor, then verify: call the `projects_list` tool yourself and report whether it answers.
4. If the connection is refused with 401, the token does not match `RAVMEM_ADMIN_TOKEN` in their `.env`;
   they should re-enter it. Do not read the `.env` for them.
