#!/usr/bin/env python3
"""Install RavMem into Antigravity (IDE and CLI).

    python3 install_to_project.py [TARGET_DIR] [--global] [--server-url URL] [--force]

Project mode writes <target>/.agents/ (mcp_config.json, rules, skills, scripts) and merges the RavMem rules into
<target>/GEMINI.md. The MCP config has no environment interpolation, so the token is never written into the
project (it would end up in git): the file gets a YOUR_RAVMEM_TOKEN placeholder to replace, or use --global, which
writes the real token into the user-private ~/.gemini/config/mcp_config.json (mode 600).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

AGY_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGY_DIR.parent / "core"))

import connect  # noqa: E402

BEGIN, END = "<!-- BEGIN RAVMEM INSTRUCTIONS -->", "<!-- END RAVMEM INSTRUCTIONS -->"
SCRIPT_FILES = ("_ravmem_http.py", "load_kg_context.py", "prune_kg.py", "check_onboarding.py")


def _server_entry(url: str, token: str) -> dict:
    return {"serverUrl": url, "headers": {"Authorization": f"Bearer {token}", "X-KG-Team": "default", "X-KG-Branch": "global"}}


def _merge_mcp(path: Path, entry: dict, force: bool, private: bool) -> None:
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError as exc:
            print(f"Error: {path} is not valid JSON ({exc}); not touching it.", file=sys.stderr)
            return
        if "ravmem" in data.get("mcpServers", {}) and not force:
            print(f"Kept existing ravmem entry in {path} (use --force to replace).")
            return
        shutil.copy2(path, path.with_suffix(".json.bak"))
    data.setdefault("mcpServers", {})["ravmem"] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if private:
        os.chmod(path, 0o600)
    print(f"Configured MCP server in {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Install RavMem into Antigravity")
    ap.add_argument("target", nargs="?", default=".", help="project directory (default: current directory)")
    ap.add_argument("--global", dest="is_global", action="store_true", help="configure ~/.gemini/config/mcp_config.json only")
    ap.add_argument("--server-url", help="RavMem server URL (default: RAVMEM_SERVER_URL, ~/.ravmem/client.json, then localhost:7432)")
    ap.add_argument("--force", "-f", action="store_true", help="replace existing configuration, rules and skills")
    args = ap.parse_args()

    server, token = connect.resolve(args.server_url)
    url = connect.mcp_url(server)

    if args.is_global:
        _merge_mcp(Path.home() / ".gemini" / "config" / "mcp_config.json", _server_entry(url, token or connect.TOKEN_PLACEHOLDER), args.force, private=True)
    else:
        target = Path(args.target).expanduser().resolve()
        if not target.is_dir():
            print(f"Error: '{target}' is not a directory.", file=sys.stderr)
            return 1
        agents = target / ".agents"
        _merge_mcp(agents / "mcp_config.json", _server_entry(url, connect.TOKEN_PLACEHOLDER), args.force, private=False)

        for sub in ("rules", "skills", "scripts"):
            (agents / sub).mkdir(parents=True, exist_ok=True)
        for rule in (AGY_DIR / "rules").glob("*.md"):
            dest = agents / "rules" / rule.name
            if args.force or not dest.exists():
                shutil.copy2(rule, dest)
        for skill in (AGY_DIR / "skills").iterdir():
            dest = agents / "skills" / skill.name
            if skill.is_dir() and (args.force or not dest.exists()):
                shutil.rmtree(dest, ignore_errors=True)
                shutil.copytree(skill, dest)
        for name in SCRIPT_FILES:
            shutil.copy2(AGY_DIR / "scripts" / name, agents / "scripts" / name)

        gemini = target / "GEMINI.md"
        fragment = (AGY_DIR / "GEMINI.md.fragment").read_text(encoding="utf-8")
        existing = gemini.read_text(encoding="utf-8") if gemini.exists() else ""
        if BEGIN in existing and END in existing:
            if args.force:
                gemini.write_text(existing.split(BEGIN)[0] + fragment.rstrip("\n") + existing.split(END, 1)[1], encoding="utf-8")
                print(f"Refreshed RavMem instructions in {gemini}")
        else:
            with open(gemini, "a", encoding="utf-8") as f:
                f.write(("\n\n" if existing and not existing.endswith("\n") else "") + fragment)
            print(f"Added RavMem instructions to {gemini}")
        print(f"Installed rules, skills and scripts under {agents}")
        if not token:
            print("No token found. Replace YOUR_RAVMEM_TOKEN in .agents/mcp_config.json (and keep that file out of git).")
        else:
            print("Replace YOUR_RAVMEM_TOKEN in .agents/mcp_config.json with your token and keep that file out of git, or re-run with --global.")

    print(f"Server check: {connect.check(server, token) or 'OK'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
