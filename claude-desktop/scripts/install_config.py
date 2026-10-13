#!/usr/bin/env python3
"""Add the RavMem MCP server to Claude Desktop's claude_desktop_config.json.

    python3 install_config.py [--config PATH] [--server-url URL] [--force]

Claude Desktop only launches local (stdio) servers from this file, so the entry runs the standard
`mcp-remote` package (via npx, needs Node.js), which connects to RavMem's Streamable HTTP endpoint.
It is not RavMem-specific code. The token goes into the entry's env block in your user-private config file.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "core"))

import connect  # noqa: E402


def default_config_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Add RavMem to Claude Desktop")
    ap.add_argument("--config", "-c", help="path to claude_desktop_config.json")
    ap.add_argument("--server-url", help="RavMem server URL (default: RAVMEM_SERVER_URL, ~/.ravmem/client.json, then localhost:7432)")
    ap.add_argument("--force", "-f", action="store_true", help="replace an existing ravmem entry")
    args = ap.parse_args()

    server, token = connect.resolve(args.server_url)
    path = (Path(args.config) if args.config else default_config_path()).expanduser().resolve()

    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError as exc:
            print(f"Error: {path} is not valid JSON ({exc}); not touching it.", file=sys.stderr)
            return 1
        if "ravmem" in data.get("mcpServers", {}) and not args.force:
            print(f"A 'ravmem' server is already configured in {path} (use --force to replace).")
            return 0
        shutil.copy2(path, path.with_suffix(".json.bak"))
        print(f"Backed up the existing config to {path.with_suffix('.json.bak')}")

    data.setdefault("mcpServers", {})["ravmem"] = {
        "command": "npx",
        "args": ["-y", "mcp-remote", connect.mcp_url(server), "--header", "Authorization:${RAVMEM_AUTH}",
                 "--header", "X-KG-Team:default", "--header", "X-KG-Branch:global"],
        "env": {"RAVMEM_AUTH": f"Bearer {token or connect.TOKEN_PLACEHOLDER}"},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)

    print(f"Configured RavMem in {path}")
    print(f"Server check: {connect.check(server, token) or 'OK'}")
    if not token:
        print("No token found: replace YOUR_RAVMEM_TOKEN in that file's env block.")
    if not shutil.which("npx"):
        print("Warning: npx was not found. Install Node.js, which Claude Desktop needs to run mcp-remote.")
    print("Restart Claude Desktop to load the server.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
