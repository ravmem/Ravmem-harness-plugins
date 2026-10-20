---
description: Index this repository in RavMem for the first time (user-invoked)
always_on: true
---

# First-Time Repository Onboarding (RavMem)

Onboarding is done by this skill end to end: **run the steps below yourself in the terminal** — do not hand
the user commands to run. Invoking this skill (or asking you to onboard/index the repo) is the user's consent
to upload the committed files to their RavMem server. Never do it on your own initiative otherwise.

The RavMem CLI does the indexing because it reads the local git repo and uploads its **committed** files;
an MCP server cannot read your disk.

1. Check whether the repo is already indexed: `projects_list()`. If the project is there and its default
   branch is ready, you are done — use the search and impact guidance. If the project exists but has no
   ready branch, skip to step 4.
2. Make sure the CLI is installed: `command -v ravmem || pip install ravmem-cli`.
3. Check the CLI can reach the server: `~/.ravmem/client.json` must exist (`ravmem auth login` writes it). If
   it is missing, this is the one thing you cannot do: ask the user to run `ravmem auth login` in their own
   terminal and continue once they confirm. Never ask for, read or print their token.
4. From the repo root, register and index it, using the repo directory name as `<project>` unless the user
   gave one:

   ```
   ravmem remote add . --name <project>         # registers the project; skip if projects_list already shows it
   ravmem analyze . --project <project> --wait  # uploads the committed files and indexes them
   ```

   `remote add` must come first: `analyze` fails with "Project not found" for an unregistered project. Add
   `--langs python,typescript` to `analyze` to limit languages. If the repo has no commits, or the CLI reports
   "no committed files", tell the user uncommitted changes are not uploaded and ask before committing anything.
5. Confirm with `projects_list()` and `jobs(project=…)`. If your branch is not the project's default branch
   (for example `master` while the project says `main`), the code tools answer "Branch … has no index" and list
   the available branches; pass `branch` or fix the default with `ravmem remote` / `PATCH /api/projects/<id>`.
   Later updates are `ravmem analyze . --project <project> --incremental` from the repo; `project_sync` also
   works for projects the server cloned itself.
