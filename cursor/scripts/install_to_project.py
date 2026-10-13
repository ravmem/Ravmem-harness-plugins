#!/usr/bin/env python3
"""Install RavMem into a Cursor project.

    python3 install_to_project.py [TARGET_DIR] [--server-url URL] [--force]

Writes <target>/.cursor/mcp.json (the server's Streamable HTTP endpoint), copies the rules to
<target>/.cursor/rules/ and the maintenance scripts to <target>/.cursor/scripts/. The token is NOT written to
the project: the config reads it from the RAVMEM_TOKEN environment variable, so mcp.json is safe to commit.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

CURSOR_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CURSOR_DIR.parent / "core"))

import connect  # noqa: E402

RULES_DIR = CURSOR_DIR / "rules"
SCRIPTS_DIR = CURSOR_DIR / "scripts"
SCRIPT_FILES = ("_ravmem_http.py", "load_kg_context.py", "prune_kg.py", "check_onboarding.py")


def main() -> int:
    ap = argparse.ArgumentParser(description="Install RavMem into a Cursor project")
    ap.add_argument("target", nargs="?", default=".", help="project directory (default: current directory)")
    ap.add_argument("--server-url", help="RavMem server URL (default: RAVMEM_SERVER_URL, ~/.ravmem/client.json, then localhost:7432)")
    ap.add_argument("--force", "-f", action="store_true", help="overwrite existing mcp.json, rules and scripts")
    args = ap.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        print(f"Error: '{target}' is not a directory.", file=sys.stderr)
        return 1
    server, token = connect.resolve(args.server_url)

    cursor_dir = target / ".cursor"
    (cursor_dir / "rules").mkdir(parents=True, exist_ok=True)
    (cursor_dir / "scripts").mkdir(parents=True, exist_ok=True)

    mcp_json = cursor_dir / "mcp.json"
    if mcp_json.exists() and not args.force:
        print(f"Kept existing {mcp_json} (use --force to overwrite).")
    else:
        config = {"mcpServers": {"ravmem": {
            "url": connect.mcp_url(server),
            "headers": {"Authorization": "Bearer ${env:RAVMEM_TOKEN}", "X-KG-Team": "default", "X-KG-Branch": "global"},
        }}}
        mcp_json.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {mcp_json}")

    copied = 0
    for src in RULES_DIR.glob("*.mdc"):
        dest = cursor_dir / "rules" / src.name
        if args.force or not dest.exists():
            shutil.copy2(src, dest)
            copied += 1
    for name in SCRIPT_FILES:
        dest = cursor_dir / "scripts" / name
        if args.force or not dest.exists():
            shutil.copy2(SCRIPTS_DIR / name, dest)
    print(f"Installed {copied} rule(s) and the maintenance scripts under {cursor_dir}")

    problem = connect.check(server, token)
    print(f"Server check: {problem or 'OK'}")
    if not token:
        print("No token found. Set it where Cursor can read it:  export RAVMEM_TOKEN=<token>  (then restart Cursor).")
    else:
        print("Make RAVMEM_TOKEN available to Cursor (export it in the shell that launches Cursor, or in your profile).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
