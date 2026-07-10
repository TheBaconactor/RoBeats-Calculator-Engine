"""Resolve and validate isolated paths for Issue #116 measurements.

The linked benchmark worktree is not necessarily the primary checkout that owns the production
FG cache.  Production-cache detection therefore follows Git's common directory to the primary
worktree instead of assuming ``<current worktree>/bin``.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXED_BENCH_ROOT = Path(r"C:\mfbench")
WINDOWS_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


@dataclass(frozen=True)
class Issue116RunPaths:
    bench_root: Path
    worktree_root: Path
    preflight_tool_root: Path
    git_common_dir: Path
    primary_worktree_root: Path
    run_root: Path
    fg_response_cache_dir: Path
    timeline_cache_dir: Path
    optimizer_bin_dir: Path
    database_path: Path
    profile_events_path: Path
    artifacts_dir: Path
    preflight_manifest_path: Path
    production_fg_cache_dir: Path

    def environment(self) -> dict[str, str]:
        return {
            "FG_RESPONSE_FRONTIER_CACHE_DIR": str(self.fg_response_cache_dir),
            "TIMELINE_FRONTIER_CACHE_DIR": str(self.timeline_cache_dir),
            "ROBEATSMETA_OPTIMIZER_BIN_DIR": str(self.optimizer_bin_dir),
            "EVOLUTION_DB_PATH": str(self.database_path),
            "METAFINDER_PROFILE_EVENTS_PATH": str(self.profile_events_path),
        }


@dataclass(frozen=True)
class _GitWorktreeContext:
    root: Path
    common_dir: Path
    primary_root: Path
    registered_roots: tuple[Path, ...]


@dataclass(frozen=True)
class _SafeWorktreeTarget:
    bench_root: Path
    target_root: Path
    tool_root: Path
    common_dir: Path
    primary_root: Path


def _canonical_path(path: Path) -> Path:
    return path.resolve(strict=True)


def _path_is_symlink(metadata: os.stat_result) -> bool:
    return stat.S_ISLNK(metadata.st_mode)


def _path_file_attributes(metadata: os.stat_result) -> int:
    return int(getattr(metadata, "st_file_attributes", 0))


def _validate_bench_root(bench_root: str | Path) -> Path:
    expected = Path(os.path.abspath(bench_root))
    try:
        metadata = os.lstat(expected)
    except OSError as exc:
        raise ValueError(f"Issue #116 fixed benchmark root does not exist: {expected}") from exc
    if _path_is_symlink(metadata):
        raise ValueError(f"Issue #116 fixed benchmark root must not be a symlink: {expected}")
    if _path_file_attributes(metadata) & WINDOWS_REPARSE_ATTRIBUTE:
        raise ValueError(
            f"Issue #116 fixed benchmark root must not be a junction or reparse point: {expected}"
        )
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"Issue #116 fixed benchmark root is not a normal directory: {expected}")
    canonical = _canonical_path(expected)
    if canonical != expected:
        raise ValueError(
            "Issue #116 fixed benchmark root canonical path differs from the literal boundary: "
            f"{expected} -> {canonical}"
        )
    return canonical


def _validated_fixed_bench_root() -> Path:
    return _validate_bench_root(FIXED_BENCH_ROOT)


def _git_subprocess_environment() -> dict[str, str]:
    environment = dict(os.environ)
    inherited_git = sorted(name for name in environment if name.upper().startswith("GIT_"))
    if inherited_git:
        raise ValueError(
            "Issue #116 Git identity checks reject inherited GIT_* environment overrides: "
            + ", ".join(inherited_git)
        )
    return environment


def _git_stdout(worktree_root: Path, *args: str) -> str:
    environment = _git_subprocess_environment()
    result = subprocess.run(
        ["git", "-C", str(worktree_root), *args],
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )
    return str(result.stdout).strip()


def _worktree_roots_from_porcelain(output: str) -> tuple[Path, ...]:
    roots = tuple(
        Path(line.removeprefix("worktree ").strip()).resolve()
        for line in output.splitlines()
        if line.startswith("worktree ")
    )
    if roots:
        return roots
    raise ValueError("git worktree list did not report any worktrees")


def _primary_worktree_from_porcelain(output: str) -> Path:
    return _worktree_roots_from_porcelain(output)[0]


def _git_worktree_context(worktree_root: str | Path) -> _GitWorktreeContext:
    worktree = Path(worktree_root).resolve()
    if not worktree.is_dir():
        raise ValueError(f"Issue #116 target is not an existing Git worktree: {worktree}")
    try:
        top_level = Path(
            _git_stdout(worktree, "rev-parse", "--path-format=absolute", "--show-toplevel")
        ).resolve()
        common_dir = Path(
            _git_stdout(worktree, "rev-parse", "--path-format=absolute", "--git-common-dir")
        ).resolve()
        registered = _worktree_roots_from_porcelain(
            _git_stdout(worktree, "worktree", "list", "--porcelain")
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"Issue #116 target is not an existing Git worktree: {worktree}") from exc
    if top_level != worktree:
        raise ValueError(f"Issue #116 target must be the Git worktree root: {worktree}")
    if worktree not in registered:
        raise ValueError(f"Issue #116 target is not a registered Git worktree: {worktree}")
    primary = registered[0]
    primary_git_dir = (primary / ".git").resolve()
    if not primary_git_dir.is_dir() or primary_git_dir != common_dir:
        raise ValueError(
            "Git primary-worktree/common-dir ownership is ambiguous; refusing to infer the "
            "production FG cache"
        )
    return _GitWorktreeContext(
        root=worktree,
        common_dir=common_dir,
        primary_root=primary,
        registered_roots=registered,
    )


def resolve_primary_worktree_root(worktree_root: str | Path = REPO_ROOT) -> Path:
    return _git_worktree_context(worktree_root).primary_root


def resolve_production_fg_cache_dir(worktree_root: str | Path = REPO_ROOT) -> Path:
    return (
        resolve_primary_worktree_root(worktree_root)
        / "bin"
        / "fg_response_frontier_cache"
    ).resolve()


def _is_equal_or_descendant(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _resolve_safe_worktree_target(
    worktree_root: str | Path | None,
) -> _SafeWorktreeTarget:
    bench = _validated_fixed_bench_root()
    tool = REPO_ROOT.resolve()
    target = Path(worktree_root).resolve() if worktree_root is not None else tool
    if target.parent != bench:
        raise ValueError(
            f"Issue #116 target worktree must be a direct child of {bench}: {target}"
        )
    if tool.parent != bench:
        raise ValueError(
            f"Issue #116 preflight tool worktree must be a direct child of {bench}: {tool}"
        )
    if not target.is_dir():
        raise ValueError(f"Issue #116 target is not an existing Git worktree: {target}")

    tool_context = _git_worktree_context(tool)
    target_context = tool_context if target == tool else _git_worktree_context(target)
    if target_context.common_dir != tool_context.common_dir:
        raise ValueError("Issue #116 target and preflight tool do not share one Git common dir")
    if target_context.primary_root != tool_context.primary_root:
        raise ValueError("Issue #116 target and preflight tool do not share one primary worktree")
    if target not in tool_context.registered_roots:
        raise ValueError(f"Issue #116 target is not registered with the preflight tool repo: {target}")
    if tool not in target_context.registered_roots:
        raise ValueError(
            f"Issue #116 preflight tool is not registered with the target repo: {tool}"
        )
    return _SafeWorktreeTarget(
        bench_root=bench,
        target_root=target,
        tool_root=tool,
        common_dir=target_context.common_dir,
        primary_root=target_context.primary_root,
    )


def _resolve_issue116_run_paths(
    run_root: str | Path,
    *,
    worktree_root: str | Path,
    bench_root: str | Path,
    production_fg_cache_dir: str | Path,
    preflight_tool_root: str | Path | None = None,
    git_common_dir: str | Path | None = None,
    primary_worktree_root: str | Path | None = None,
    fg_response_cache_dir: str | Path | None = None,
    timeline_cache_dir: str | Path | None = None,
    database_path: str | Path | None = None,
    profile_events_path: str | Path | None = None,
    artifacts_dir: str | Path | None = None,
) -> Issue116RunPaths:
    root = Path(run_root).resolve()
    bench = Path(bench_root).resolve()
    if root.parent != bench:
        raise ValueError(f"Issue #116 run root must be a direct named child of {bench}: {root}")
    worktree = Path(worktree_root).resolve()
    if worktree.parent != bench:
        raise ValueError(
            f"Issue #116 target worktree must be a direct child of {bench}: {worktree}"
        )
    if worktree == root:
        raise ValueError("Issue #116 target worktree and run root must be distinct")
    tool = Path(preflight_tool_root or worktree).resolve()
    if tool.parent != bench:
        raise ValueError(
            f"Issue #116 preflight tool worktree must be a direct child of {bench}: {tool}"
        )
    if tool == root:
        raise ValueError("Issue #116 preflight tool worktree and run root must be distinct")

    production = Path(production_fg_cache_dir).resolve()
    primary = Path(primary_worktree_root or production.parent.parent).resolve()
    resolved = Issue116RunPaths(
        bench_root=bench,
        worktree_root=worktree,
        preflight_tool_root=tool,
        git_common_dir=Path(git_common_dir or primary / ".git").resolve(),
        primary_worktree_root=primary,
        run_root=root,
        fg_response_cache_dir=Path(
            fg_response_cache_dir or root / "fg_response_frontier_cache"
        ).resolve(),
        timeline_cache_dir=Path(
            timeline_cache_dir or root / "timeline_frontier_cache"
        ).resolve(),
        optimizer_bin_dir=(root / "optimizer_bin").resolve(),
        database_path=Path(database_path or root / "evolution.db").resolve(),
        profile_events_path=Path(
            profile_events_path or root / "profile_events.jsonl"
        ).resolve(),
        artifacts_dir=Path(artifacts_dir or root / "artifacts").resolve(),
        preflight_manifest_path=(root / "preflight.json").resolve(),
        production_fg_cache_dir=production,
    )

    if _is_equal_or_descendant(resolved.fg_response_cache_dir, production):
        raise ValueError(
            "FG_RESPONSE_FRONTIER_CACHE_DIR resolves to the production cache or one of its "
            f"descendants: {resolved.fg_response_cache_dir}"
        )

    isolated = {
        "FG response cache": resolved.fg_response_cache_dir,
        "timeline cache": resolved.timeline_cache_dir,
        "optimizer bin": resolved.optimizer_bin_dir,
        "database": resolved.database_path,
        "profile events": resolved.profile_events_path,
        "artifacts": resolved.artifacts_dir,
        "preflight manifest": resolved.preflight_manifest_path,
    }
    items = list(isolated.items())
    for idx, (left_label, left) in enumerate(items):
        for right_label, right in items[idx + 1 :]:
            if _is_equal_or_descendant(left, right) or _is_equal_or_descendant(right, left):
                raise ValueError(
                    f"Issue #116 isolated paths overlap: {left_label}={left}, "
                    f"{right_label}={right}"
                )
    for label, path in isolated.items():
        if not _is_equal_or_descendant(path, root) or path == root:
            raise ValueError(f"Issue #116 {label} path escapes its run root: {path}")
    return resolved


def resolve_issue116_run_paths(
    run_root: str | Path,
    *,
    worktree_root: str | Path | None = None,
    fg_response_cache_dir: str | Path | None = None,
    timeline_cache_dir: str | Path | None = None,
    database_path: str | Path | None = None,
    profile_events_path: str | Path | None = None,
    artifacts_dir: str | Path | None = None,
) -> Issue116RunPaths:
    """Resolve one run without caller-overridable safety roots or production-cache ownership."""
    target = _resolve_safe_worktree_target(worktree_root)
    production = (
        target.primary_root / "bin" / "fg_response_frontier_cache"
    ).resolve()
    return _resolve_issue116_run_paths(
        run_root,
        worktree_root=target.target_root,
        bench_root=target.bench_root,
        production_fg_cache_dir=production,
        preflight_tool_root=target.tool_root,
        git_common_dir=target.common_dir,
        primary_worktree_root=target.primary_root,
        fg_response_cache_dir=fg_response_cache_dir,
        timeline_cache_dir=timeline_cache_dir,
        database_path=database_path,
        profile_events_path=profile_events_path,
        artifacts_dir=artifacts_dir,
    )


def _git_state(worktree_root: Path) -> tuple[str, str]:
    head_before = _git_stdout(worktree_root, "rev-parse", "HEAD")
    tracked_status = _git_stdout(
        worktree_root,
        "status",
        "--porcelain",
        "--untracked-files=all",
    )
    head_after = _git_stdout(worktree_root, "rev-parse", "HEAD")
    if head_before != head_after:
        raise ValueError(
            "Issue #116 worktree HEAD changed while reading status: "
            f"{head_before} -> {head_after}"
        )
    return head_before, tracked_status


def _run_payload(
    paths: Issue116RunPaths,
    *,
    git_head: str,
    preflight_tool_git_head: str,
) -> dict:
    return {
        "git_head": str(git_head),
        "target_worktree": {
            "root": str(paths.worktree_root),
            "git_head": str(git_head),
        },
        "preflight_tool": {
            "root": str(paths.preflight_tool_root),
            "git_head": str(preflight_tool_git_head),
        },
        "paths": {key: str(value) for key, value in asdict(paths).items()},
        "environment": paths.environment(),
    }


def _require_clean_exact_head(git_state: tuple[str, str], *, owner: str) -> str:
    head, tracked_status = git_state
    exact_head = str(head).strip()
    if re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", exact_head) is None:
        raise ValueError(f"Issue #116 {owner} did not resolve a full exact Git HEAD")
    if str(tracked_status).strip():
        raise ValueError(
            f"Issue #116 {owner} requires no tracked or untracked worktree changes: "
            f"{tracked_status.strip()}"
        )
    return exact_head


def _prepare_issue116_run(
    paths: Issue116RunPaths,
    *,
    git_state: tuple[str, str],
    preflight_tool_git_state: tuple[str, str] | None = None,
    publication_state_reader: Callable[[Path], tuple[str, str]],
) -> dict:
    """Create one fresh run root after proving all visible sources equal an exact HEAD."""
    if preflight_tool_git_state is None:
        if paths.preflight_tool_root != paths.worktree_root:
            raise ValueError(
                "Issue #116 sibling-target preparation requires the preflight tool Git state"
            )
        preflight_tool_git_state = git_state
    exact_head = _require_clean_exact_head(git_state, owner="target worktree")
    tool_head = _require_clean_exact_head(
        preflight_tool_git_state,
        owner="preflight tool worktree",
    )
    validated_bench = _validate_bench_root(paths.bench_root)
    if paths.run_root.parent != validated_bench:
        raise ValueError(
            f"Issue #116 run root left the fixed benchmark boundary: {paths.run_root}"
        )

    try:
        paths.run_root.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise ValueError(f"Issue #116 run root already exists: {paths.run_root}") from exc
    for directory in (
        paths.fg_response_cache_dir,
        paths.timeline_cache_dir,
        paths.optimizer_bin_dir,
        paths.artifacts_dir,
        paths.database_path.parent,
        paths.profile_events_path.parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    publication_target_state = publication_state_reader(paths.worktree_root)
    publication_tool_state = (
        publication_target_state
        if paths.preflight_tool_root == paths.worktree_root
        else publication_state_reader(paths.preflight_tool_root)
    )
    if publication_target_state != git_state:
        raise ValueError(
            "Issue #116 target Git state changed between validation and manifest publication"
        )
    if publication_tool_state != preflight_tool_git_state:
        raise ValueError(
            "Issue #116 preflight tool Git state changed between validation and manifest publication"
        )

    payload = _run_payload(
        paths,
        git_head=exact_head,
        preflight_tool_git_head=tool_head,
    )
    with paths.preflight_manifest_path.open("x", encoding="utf-8") as manifest:
        manifest.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def prepare_issue116_run(paths: Issue116RunPaths) -> dict:
    """Prepare only an exact path bundle produced by the safe public resolver."""
    resolved = resolve_issue116_run_paths(
        paths.run_root,
        worktree_root=paths.worktree_root,
        fg_response_cache_dir=paths.fg_response_cache_dir,
        timeline_cache_dir=paths.timeline_cache_dir,
        database_path=paths.database_path,
        profile_events_path=paths.profile_events_path,
        artifacts_dir=paths.artifacts_dir,
    )
    if paths != resolved:
        raise ValueError(
            "Issue #116 preparation requires the exact path bundle from "
            "resolve_issue116_run_paths"
        )
    target_git_state = _git_state(resolved.worktree_root)
    tool_git_state = (
        target_git_state
        if resolved.preflight_tool_root == resolved.worktree_root
        else _git_state(resolved.preflight_tool_root)
    )
    return _prepare_issue116_run(
        resolved,
        git_state=target_git_state,
        preflight_tool_git_state=tool_git_state,
        publication_state_reader=_git_state,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True)
    parser.add_argument(
        "--worktree-root",
        help="registered same-repository target worktree (defaults to this tool checkout)",
    )
    parser.add_argument("--fg-cache-dir")
    parser.add_argument("--timeline-cache-dir")
    parser.add_argument("--database-path")
    parser.add_argument("--profile-events-path")
    parser.add_argument("--artifacts-dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    paths = resolve_issue116_run_paths(
        args.run_root,
        worktree_root=args.worktree_root,
        fg_response_cache_dir=args.fg_cache_dir,
        timeline_cache_dir=args.timeline_cache_dir,
        database_path=args.database_path,
        profile_events_path=args.profile_events_path,
        artifacts_dir=args.artifacts_dir,
    )
    payload = prepare_issue116_run(paths)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
