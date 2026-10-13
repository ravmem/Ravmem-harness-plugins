#!/usr/bin/env python3
"""SessionStart hook: suggest indexing the repo once, when the server has no project for it.

Silent (exit 0, no output) when the working directory is not a git repository, when a project with this
repository's name or path is already registered, or when the server is unreachable or rejects the token
(this is a hint, not a health check; the ravmem-status guidance covers diagnostics).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ravmem_http import RavMemError, list_projects  # noqa: E402


def _repo_root(path: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", path, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def main() -> int:
    root = _repo_root(str(Path.cwd()))
    if not root:
        return 0
    try:
        projects = list_projects()
    except RavMemError:
        return 0

    name = Path(root).name.lower()
    for p in projects:
        known = {str(p.get(k) or "").rstrip("/").lower() for k in ("id", "name", "path", "repo_path")}
        if name in known or root.rstrip("/").lower() in known:
            return 0

    print(
        f"[RavMem] No project named '{Path(root).name}' is indexed on the server yet. To enable code search and "
        "impact analysis, run `ravmem analyze . --wait` from the repo root (or ask for the ravmem-onboarding guidance)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
