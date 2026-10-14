"""Minimal stdlib REST helper for the RavMem session hooks and maintenance scripts.

The MCP tools are only reachable from inside a model session. Hooks run before the model starts (and
prune_kg runs from a shell), so they call the server's REST API directly. Standard library only: the
scripts are copied into harness plugin directories and project folders, so they must not import
anything from this repository.

Settings come from RAVMEM_<NAME> environment variables, or from CLAUDE_PLUGIN_OPTION_<NAME> (the form in
which Claude Code passes a plugin's configured options to its hooks). Empty strings count as unset.
Server and token resolution, first match wins:
  1. those environment variables (RAVMEM_SERVER_URL, RAVMEM_TOKEN)
  2. ~/.ravmem/client.json  (server_url, api_key) - the file `ravmem auth login` writes
  3. server http://localhost:7432
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_SERVER = "http://localhost:7432"
CREDENTIALS_PATH = Path.home() / ".ravmem" / "client.json"


class RavMemError(RuntimeError):
    """Any failure talking to the server; the message is safe to show to a user."""


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def setting(name: str) -> str | None:
    """RAVMEM_<NAME>, else CLAUDE_PLUGIN_OPTION_<NAME>; None when unset or empty."""
    return _clean(os.environ.get(f"RAVMEM_{name}")) or _clean(os.environ.get(f"CLAUDE_PLUGIN_OPTION_{name}"))


def resolve() -> tuple[str, str | None]:
    """Return (server_url, token). The token may be None for an unauthenticated server."""
    url, token = setting("SERVER_URL"), setting("TOKEN")
    if not (url and token) and CREDENTIALS_PATH.exists():
        try:
            creds = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            creds = {}
        url = url or _clean(creds.get("server_url"))
        token = token or _clean(creds.get("api_key"))
    return (url or DEFAULT_SERVER).rstrip("/"), token


def kg_scope() -> tuple[str, str]:
    """(team, branch) the memory tools use, mirroring the X-KG-* headers in the MCP client config."""
    return setting("KG_TEAM") or "default", setting("KG_BRANCH") or "global"


def request(method: str, path: str, *, params: dict[str, Any] | None = None, timeout: float = 5.0) -> Any:
    server, token = resolve()
    team, branch = kg_scope()
    query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    req = urllib.request.Request(
        f"{server}{path}{'?' + query if query else ''}",
        method=method,
        headers={
            "Accept": "application/json",
            "X-KG-Team": team,
            "X-KG-Branch": branch,
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RavMemError("RavMem rejected the token (401): it may be expired or wrong for this server.") from exc
        if exc.code == 403:
            raise RavMemError(f"RavMem denied {method} {path} (403): the token lacks the needed permission.") from exc
        raise RavMemError(f"RavMem returned {exc.code} for {method} {path}") from exc
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        raise RavMemError(f"Could not reach RavMem at {server}: {exc}") from exc


def list_nodes(node_type: str | None = None, *, active_only: bool = True, timeout: float = 5.0) -> list[dict[str, Any]]:
    """Memory nodes in the configured team/branch. node_type is the canonical name, e.g. "Task"."""
    data = request(
        "GET", "/api/knowledge/neurons",
        params={"node_type": node_type, "active_only": "true" if active_only else "false"},
        timeout=timeout,
    )
    return [n for n in (data or []) if isinstance(n, dict)]


def deactivate_node(node_id: str) -> None:
    request("DELETE", f"/api/knowledge/neurons/{urllib.parse.quote(node_id, safe='')}")


def list_projects(timeout: float = 3.0) -> list[dict[str, Any]]:
    data = request("GET", "/api/projects", timeout=timeout)
    return [p for p in (data or []) if isinstance(p, dict)]
