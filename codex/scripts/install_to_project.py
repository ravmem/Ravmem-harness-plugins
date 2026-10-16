#!/usr/bin/env python3
"""Install RavMem into Codex CLI.

    python3 install_to_project.py [TARGET_DIR] [--global] [--server-url URL] [--force]

Adds [mcp_servers.ravmem] (Streamable HTTP, token read from the RAVMEM_TOKEN environment variable) to
<target>/.codex/config.toml, or to ~/.codex/config.toml with --global (which also installs the ravmem-setup and ravmem-configure prompts). Unless --global, it also merges the
RavMem rules into <target>/AGENTS.md and copies the maintenance scripts to <target>/.codex/scripts/.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

CODEX_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODEX_DIR.parent / "core"))

import connect  # noqa: E402

FRAGMENT_FILE = CODEX_DIR / "AGENTS.md.fragment"
PROMPTS_DIR = CODEX_DIR / "prompts"
SCRIPTS_DIR = CODEX_DIR / "scripts"
SCRIPT_FILES = ("_ravmem_http.py", "load_kg_context.py", "prune_kg.py", "check_onboarding.py")
BEGIN, END = "<!-- BEGIN RAVMEM INSTRUCTIONS -->", "<!-- END RAVMEM INSTRUCTIONS -->"

CONFIG_TEMPLATE = """
[mcp_servers.ravmem]
url = "{url}"
bearer_token_env_var = "RAVMEM_TOKEN"

[mcp_servers.ravmem.http_headers]
X-KG-Team = "default"
X-KG-Branch = "global"
"""


def _add_server(config_file: Path, url: str, force: bool) -> None:
    content = config_file.read_text(encoding="utf-8") if config_file.exists() else ""
    if "[mcp_servers.ravmem]" in content:
        if not force:
            print(f"Kept existing [mcp_servers.ravmem] in {config_file} (use --force to add a fresh block).")
            return
        print(f"Note: --force appends a new block; remove the old [mcp_servers.ravmem] tables from {config_file} by hand.")
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "a", encoding="utf-8") as f:
        f.write(CONFIG_TEMPLATE.format(url=url))
    print(f"Configured MCP server in {config_file}")


def _merge_agents(agents_file: Path, force: bool) -> None:
    fragment = FRAGMENT_FILE.read_text(encoding="utf-8")
    existing = agents_file.read_text(encoding="utf-8") if agents_file.exists() else ""
    if BEGIN in existing and END in existing:
        if not force:
            print(f"Kept existing RavMem instructions in {agents_file} (use --force to refresh).")
            return
        merged = existing.split(BEGIN)[0] + fragment.rstrip("\n") + existing.split(END, 1)[1]
        agents_file.write_text(merged, encoding="utf-8")
        print(f"Refreshed RavMem instructions in {agents_file}")
        return
    with open(agents_file, "a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n\n")
        f.write(fragment)
    print(f"Added RavMem instructions to {agents_file}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Install RavMem into Codex CLI")
    ap.add_argument("target", nargs="?", default=".", help="project directory (default: current directory)")
    ap.add_argument("--global", dest="is_global", action="store_true", help="configure ~/.codex/config.toml only")
    ap.add_argument("--server-url", help="RavMem server URL (default: RAVMEM_SERVER_URL, ~/.ravmem/client.json, then localhost:7432)")
    ap.add_argument("--force", "-f", action="store_true", help="refresh existing configuration and instructions")
    args = ap.parse_args()

    server, token = connect.resolve(args.server_url)
    url = connect.mcp_url(server)

    if args.is_global:
        codex_home = Path.home() / ".codex"
        _add_server(codex_home / "config.toml", url, args.force)
        # The setup/configure helpers are user-level custom prompts (/prompts:ravmem-setup); Codex reads those from ~/.codex/prompts.
        (codex_home / "prompts").mkdir(parents=True, exist_ok=True)
        for src in PROMPTS_DIR.glob("*.md"):
            shutil.copy2(src, codex_home / "prompts" / src.name)
        print(f"Installed the /prompts:ravmem-setup and /prompts:ravmem-configure prompts under {codex_home}")
    else:
        target = Path(args.target).expanduser().resolve()
        if not target.is_dir():
            print(f"Error: '{target}' is not a directory.", file=sys.stderr)
            return 1
        _add_server(target / ".codex" / "config.toml", url, args.force)
        _merge_agents(target / "AGENTS.md", args.force)
        scripts_dest = target / ".codex" / "scripts"
        scripts_dest.mkdir(parents=True, exist_ok=True)
        for name in SCRIPT_FILES:
            shutil.copy2(SCRIPTS_DIR / name, scripts_dest / name)
        print(f"Installed maintenance scripts to {scripts_dest}")

    print(f"Server check: {connect.check(server, token) or 'OK'}")
    print("Export your token before starting Codex:  export RAVMEM_TOKEN=<token>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
