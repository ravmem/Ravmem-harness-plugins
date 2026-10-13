"""Connection settings shared by the harness installers.

Every supported harness talks to the RavMem server's standard MCP endpoint (Streamable HTTP at
<server>/mcp) with a bearer token. This module only decides which server and token to write into a
harness config; it never talks to the server except for the optional reachability probe.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_SERVER = "http://localhost:7432"
CREDENTIALS_PATH = Path.home() / ".ravmem" / "client.json"
TOKEN_ENV_VAR = "RAVMEM_TOKEN"
TOKEN_PLACEHOLDER = "YOUR_RAVMEM_TOKEN"


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def resolve(server_url: str | None = None, token: str | None = None) -> tuple[str, str | None]:
    """(server_url, token): explicit argument > environment > ~/.ravmem/client.json > localhost default."""
    url = _clean(server_url) or _clean(os.environ.get("RAVMEM_SERVER_URL"))
    tok = _clean(token) or _clean(os.environ.get(TOKEN_ENV_VAR))
    if not (url and tok) and CREDENTIALS_PATH.exists():
        try:
            creds = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            creds = {}
        url = url or _clean(creds.get("server_url"))
        tok = tok or _clean(creds.get("api_key"))
    return (url or DEFAULT_SERVER).rstrip("/"), tok


def mcp_url(server_url: str) -> str:
    return server_url.rstrip("/") + "/mcp"


def check(server_url: str, token: str | None, timeout: float = 3.0) -> str | None:
    """None when the MCP catalog answers, else a one-line reason. Uses GET /api/mcp/tools."""
    req = urllib.request.Request(
        server_url.rstrip("/") + "/api/mcp/tools",
        headers={"Authorization": f"Bearer {token}"} if token else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return None
    except urllib.error.HTTPError as exc:
        return f"server answered {exc.code}" + (" (token rejected)" if exc.code in (401, 403) else "")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return f"cannot reach {server_url}: {exc}"
