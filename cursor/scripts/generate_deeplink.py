#!/usr/bin/env python3
"""Print a Cursor one-click install link for the RavMem MCP server.

    cursor://anysphere.cursor-deeplink/mcp/install?name=ravmem&config=<base64 json>

By default the link carries no secret: the Authorization header reads RAVMEM_TOKEN from the environment of the
Cursor process. Pass --token only for a personal link you will not share.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "core"))

import connect  # noqa: E402


def generate_deeplink(server_url: str, token: str | None = None) -> str:
    bearer = f"Bearer {token}" if token else "Bearer ${env:RAVMEM_TOKEN}"
    config = {"url": connect.mcp_url(server_url), "headers": {"Authorization": bearer}}
    encoded = base64.b64encode(json.dumps(config).encode("utf-8")).decode("ascii")
    return f"cursor://anysphere.cursor-deeplink/mcp/install?name=ravmem&config={urllib.parse.quote(encoded)}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a Cursor MCP install link")
    ap.add_argument("--server-url", help="RavMem server URL (default: discovered, then http://localhost:7432)")
    ap.add_argument("--token", help="embed this token in the link (do not share the link)")
    args = ap.parse_args()
    server, _ = connect.resolve(args.server_url)
    url = generate_deeplink(server, args.token)
    print(url)
    print(f"\n[Install RavMem in Cursor]({url})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
