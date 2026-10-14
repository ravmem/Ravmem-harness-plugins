#!/usr/bin/env python3
"""Deactivate stale RavMem memory: resolved blockers, old context notes and old low-confidence learnings.

    python3 prune_kg.py [--days 30] [--dry-run] [--auto]

Deactivation is a soft delete: the node stays in the graph but stops appearing in recall. The age
threshold defaults to RAVMEM_KG_PRUNE_STALE_DAYS (30 if unset). Team and branch come from RAVMEM_KG_TEAM and
RAVMEM_KG_BRANCH (default "default" / "global"), the same values the MCP client config sends as headers.
Needs the kg:read and kg:write permissions.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ravmem_http import RavMemError, deactivate_node, kg_scope, list_nodes, setting  # noqa: E402

LOW_CONFIDENCE = 0.5


def _parse_time(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)


def find_stale(nodes: list[dict[str, Any]], threshold_days: int) -> list[tuple[dict[str, Any], str]]:
    """(node, reason) for each node worth deactivating."""
    now = datetime.datetime.now(datetime.timezone.utc)
    max_age = datetime.timedelta(days=threshold_days)
    found = []
    for n in nodes:
        if not n.get("active", True):
            continue
        kind = str(n.get("type", "")).lower()
        created = _parse_time(n.get("created_at") or n.get("updated_at"))
        old = created is not None and now - created > max_age

        if kind == "blocker" and n.get("status") == "resolved":
            found.append((n, "Resolved blocker"))
        elif kind == "learning" and old and not n.get("validated_by_human"):
            confidence = n.get("confidence")  # absent when the server runs without confidence scoring
            if confidence is not None and float(confidence) < LOW_CONFIDENCE and int(n.get("evidence_count") or 1) <= 1:
                found.append((n, f"Uncorroborated learning, confidence {float(confidence):.2f}, older than {threshold_days} days"))
        elif kind == "context" and old:
            found.append((n, f"Context note older than {threshold_days} days"))
    return found


def main() -> int:
    default_days = int(setting("KG_PRUNE_STALE_DAYS") or "30")
    ap = argparse.ArgumentParser(description="Deactivate stale RavMem memory nodes")
    ap.add_argument("--days", type=int, default=default_days, help=f"age threshold in days (default {default_days})")
    ap.add_argument("--dry-run", action="store_true", help="list candidates without changing anything")
    ap.add_argument("--auto", action="store_true", help="deactivate without asking for confirmation")
    args = ap.parse_args()

    team, branch = kg_scope()
    try:
        nodes = list_nodes(None, active_only=True, timeout=30.0)
    except RavMemError as exc:
        print(f"Could not read memory: {exc}", file=sys.stderr)
        return 1

    stale = find_stale(nodes, args.days)
    if not stale:
        print(f"Nothing to prune in team '{team}', branch '{branch}' (threshold {args.days} days).")
        return 0

    print(f"{len(stale)} candidate(s) in team '{team}', branch '{branch}':")
    for n, reason in stale:
        print(f"  [{n.get('type', 'node')}] {str(n.get('id', ''))[:8]}  {str(n.get('label', ''))[:60]!r}  {reason}")
    if args.dry_run:
        print("Dry run: nothing was changed.")
        return 0
    if not args.auto and input("Deactivate these nodes? [y/N] ").strip().lower() not in ("y", "yes"):
        print("Cancelled.")
        return 0

    done = 0
    for n, _ in stale:
        try:
            deactivate_node(str(n["id"]))
            done += 1
        except RavMemError as exc:
            print(f"Could not deactivate {n.get('id')}: {exc}", file=sys.stderr)
    print(f"Deactivated {done} of {len(stale)}.")
    return 0 if done == len(stale) else 1


if __name__ == "__main__":
    raise SystemExit(main())
