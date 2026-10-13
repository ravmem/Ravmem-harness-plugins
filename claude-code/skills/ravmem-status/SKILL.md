---
name: ravmem-status
description: Check RavMem project/branch index status and background job health — use for diagnostics, before trusting search/impact results right after a big change or branch switch, or when the user asks whether RavMem is working.
allowed-tools: ["mcp__ravmem__projects_list", "mcp__ravmem__project_sync", "mcp__ravmem__jobs"]
---

Use for diagnostics, not routine navigation.

- `projects_list()` — every project with each branch's index status. A branch must be `ready` before the
  code tools can use it. Check it before relying on search or impact results right after switching
  branches or a large merge, and say so if the index is behind the code before answering from it.
- `project_sync(project, branch?, mode="auto")` — bring the index up to date. It fetches new commits for
  projects the server has cloned and re-indexes only what changed. It waits up to `wait_seconds`
  (default 20, max 50) and reports progress; if the job is still running it returns the job id.
  For a project uploaded from a laptop there is no remote to fetch: `project_sync` only re-indexes the files
  already stored on the server, so new local commits need `ravmem analyze . --project <project> --incremental
  --wait` from the repo.
- `jobs(job_id)` — one job's status and progress; `jobs(project=…, branch=…)` — recent jobs. Use it to
  see whether an indexing job is running, failed or stuck, especially after onboarding or a re-index.

If a call fails with a licensing error, tell the user; do not retry. Fix an unhealthy index with
`project_sync`, then confirm with `jobs`; don't answer from outdated results.
