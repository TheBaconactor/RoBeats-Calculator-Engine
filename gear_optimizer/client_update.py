from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from gear_optimizer.frontier_client import frontier_client_enabled, sync_code_from_server

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClientUpdateResult:
    enabled: bool
    updated: bool = False
    before: str = ""
    after: str = ""


def _local_revision(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD^{commit}"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _initial_managed_files(repo_root: Path) -> set[tuple[str, str]]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    managed: set[tuple[str, str]] = set()
    for relative in result.stdout.split("\0"):
        path = PurePosixPath(relative)
        if (
            not relative
            or path.is_absolute()
            or ".." in path.parts
            or relative == "config.ini"
            or relative.startswith("Data/")
        ):
            continue
        managed.add(("code", relative))
    return managed


def update_client_checkout(repo_root: str | Path | None = None) -> ClientUpdateResult:
    if not frontier_client_enabled():
        return ClientUpdateResult(enabled=False)
    root = (Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]).resolve()
    if not (root / ".git").is_dir() or not (root / "main.py").is_file() or not (root / "gear_optimizer").is_dir():
        raise RuntimeError("standalone MetaFinder must be installed from its authorized Git repository")
    before = _local_revision(root)
    sync = sync_code_from_server(root, initial_managed_files=_initial_managed_files(root))
    updated = bool(sync.downloaded_bundles or sync.removed_files)
    if updated:
        logger.info(
            "[ClientUpdate] MetaFinder installed server revision %s (%s bundles)",
            sync.code_revision[:12],
            sync.downloaded_bundles,
        )
    return ClientUpdateResult(
        enabled=True,
        updated=updated,
        before=before,
        after=sync.code_revision,
    )


def update_and_restart_client() -> ClientUpdateResult:
    result = update_client_checkout()
    if result.updated:
        os.execv(sys.executable, [sys.executable, *sys.argv])
    return result
