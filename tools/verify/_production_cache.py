"""The production FG cache of the primary worktree, which the bundle-compare tools refuse to read."""

from __future__ import annotations

import subprocess
from pathlib import Path


def resolve_production_fg_cache_dir(worktree_root: str | Path) -> Path:
    common_dir = Path(
        subprocess.run(
            ["git", "-C", str(worktree_root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    ).resolve()
    if common_dir.name != ".git":
        raise ValueError(f"cannot infer the primary worktree from git common dir {common_dir}")
    return (common_dir.parent / "bin" / "fg_response_frontier_cache").resolve()
