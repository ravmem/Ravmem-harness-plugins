# RavMem for Claude Code

A Claude Code plugin: it connects to RavMem's `/mcp` endpoint directly (`type: http`), adds five skills, and
runs two SessionStart hooks.

## Install

```
/plugin marketplace add ravmem/Ravmem-harness-plugins
/plugin install ravmem@ravmem-integrations
```

Claude Code then asks for the plugin options:

| Option | Default | Notes |
|---|---|---|
| `server_url` | `http://localhost:7432` | Base URL, no `/mcp`, no trailing slash |
| `token` | — | Stored as a sensitive value |
| `kg_team` / `kg_branch` | `default` / `global` | Memory scope, sent as `X-KG-Team` / `X-KG-Branch` |
| `kg_auto_load` | on | List the team's open tasks at session start |
| `kg_auto_record` | on | Let the agent record decisions and learnings |
| `kg_prune_stale_days` | 30 | Threshold for `scripts/prune_kg.py` |

## What it adds

- **MCP connection** — `.mcp.json`; tools appear as `mcp__ravmem__<tool>`. The server's prompts show up as slash
  commands (`session_start`, `pre_edit_impact`, `onboard_repo`, `session_handoff`, `review_learnings`).
- **Skills** — `ravmem-search`, `ravmem-impact`, `ravmem-memory`, `ravmem-status`, `ravmem-onboarding`
  (user-invoked only).
- **Hooks** — `check_onboarding.py` suggests `ravmem analyze` when the server has no project for the repo;
  `load_kg_context.py` lists open tasks. Both exit silently if the server is unreachable.
- **Maintenance** — `python3 scripts/prune_kg.py --dry-run` deactivates resolved blockers, old context notes and
  old uncorroborated learnings.

## Check it

`/mcp` in Claude Code should list `ravmem` as connected with 18 tools. If not, confirm
`curl -H "Authorization: Bearer $TOKEN" <server_url>/api/mcp/tools` answers.
