---
name: ravmem-onboarding
description: Set up RavMem for this repo for the first time — registers the project and indexes it. User-invoked only; not something to trigger automatically mid-task.
disable-model-invocation: true
allowed-tools: ["mcp__ravmem__projects_list", "mcp__ravmem__project_sync", "mcp__ravmem__jobs"]
---

Indexing a repository from a developer machine is done with the RavMem CLI, because it reads the
local git repo and uploads its **committed** files; an MCP server cannot read your disk.

1. Check whether the repo is already indexed: `projects_list()`. If the project is there and its default
   branch is ready, you are done — use the search and impact guidance.
2. Otherwise ask the user to run, from the repo root:

   ```
   pip install ravmem-cli      # once
   ravmem analyze . --wait
   ```

   Add `--project <name>` to name the project and `--langs python,typescript` to limit languages. The CLI
   reads the server URL and token from `~/.ravmem/client.json` (`ravmem auth login` writes it), or accept
   `--remote <url>`.
3. Requirements: the repo is a git repository with at least one commit. Uncommitted changes are not
   uploaded; if the CLI reports "no committed files", commit first.
4. Confirm with `projects_list()` and `jobs(project=…)`. Later updates are `ravmem analyze . --incremental`
   from the repo, or `project_sync` for projects the server has cloned itself.

Do not run the CLI for the user unprompted — it uploads source code to the server.
