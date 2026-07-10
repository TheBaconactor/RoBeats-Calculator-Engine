"""Build one isolated Issue #116 FG response-frontier corpus chart.

The runner deliberately imports only the standard library until it has validated the preflight
manifest, isolated paths, Git state, tracked inputs, environment, and Windows commit capacity.
It is intended to be executed from the detached target worktree while the maintained runner may
itself live in a sibling candidate worktree recorded by the preflight manifest.
"""
from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
import importlib
import json
import math
import os
import platform
import re
import stat
import subprocess
import sys
import threading
import time
import traceback
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


_COMPLETED_REPORT_NAME = "completed_build.json"
_FAILURE_REPORT_NAME = "failure.json"
_REQUIRED_HEADROOM_BYTES = 13_000_000_000
_SAMPLE_INTERVAL_SECONDS = 5.0
_FIXED_BENCH_ROOT = Path(r"C:\mfbench")
_WINDOWS_REPARSE_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_EXPECTED_MANIFEST_KEYS = frozenset(
    {"git_head", "target_worktree", "preflight_tool", "paths", "environment"}
)
_EXPECTED_OWNER_KEYS = frozenset({"root", "git_head"})
_EXPECTED_PATH_KEYS = frozenset(
    {
        "worktree_root",
        "bench_root",
        "preflight_tool_root",
        "git_common_dir",
        "primary_worktree_root",
        "run_root",
        "fg_response_cache_dir",
        "timeline_cache_dir",
        "optimizer_bin_dir",
        "database_path",
        "profile_events_path",
        "artifacts_dir",
        "preflight_manifest_path",
        "production_fg_cache_dir",
    }
)
_EXPECTED_ENV_KEYS = frozenset(
    {
        "FG_RESPONSE_FRONTIER_CACHE_DIR",
        "TIMELINE_FRONTIER_CACHE_DIR",
        "ROBEATSMETA_OPTIMIZER_BIN_DIR",
        "EVOLUTION_DB_PATH",
        "METAFINDER_PROFILE_EVENTS_PATH",
    }
)
_ENV_PATH_FIELDS = {
    "FG_RESPONSE_FRONTIER_CACHE_DIR": "fg_response_cache_dir",
    "TIMELINE_FRONTIER_CACHE_DIR": "timeline_cache_dir",
    "ROBEATSMETA_OPTIMIZER_BIN_DIR": "optimizer_bin_dir",
    "EVOLUTION_DB_PATH": "database_path",
    "METAFINDER_PROFILE_EVENTS_PATH": "profile_events_path",
}
_RECORDED_ENV_KEYS = (
    *_EXPECTED_ENV_KEYS,
    "METAFINDER_CONFIG_PATH",
    "PYTHONHASHSEED",
    "PYTHONPYCACHEPREFIX",
    "NUMBA_CACHE_DIR",
    "NUMBA_NUM_THREADS",
    "NUMBA_THREADING_LAYER",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "ROBEATSMETA_LIVE_CACHE_IDLE_TTL_SECONDS",
)
_HEX_HEAD_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
_SHA256_RE = re.compile(r"[0-9a-fA-F]{64}\Z")


@dataclass(frozen=True)
class _ManifestPaths:
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


@dataclass(frozen=True)
class _ManifestContext:
    paths: _ManifestPaths
    target_head: str
    tool_head: str
    environment: dict[str, str]


@dataclass(frozen=True)
class _GitState:
    root: Path
    head: str
    status: str


@dataclass(frozen=True)
class _InputSnapshot:
    path: Path
    relative_path: str
    sha256: str
    git_blob: str
    size: int
    mtime_ns: int
    device: int
    inode: int


@dataclass(frozen=True)
class _HashedFile:
    path: Path
    sha256: str
    size: int
    mtime_ns: int
    device: int
    inode: int


@dataclass(frozen=True)
class _Runtime:
    np: Any
    numba: Any
    psutil: Any
    read_table: Callable[..., Any]
    get_base_calc_song: Callable[..., Any]
    build_ref_arrays_from_stats: Callable[..., Any]
    prebuild: Any
    reducer: Any
    cache_types: Any
    constants: Any
    config: Any


@dataclass(frozen=True)
class _Dependencies:
    run_git: Callable[[Path, Sequence[str]], str]
    read_capacity: Callable[[], dict[str, int]]
    read_hardware: Callable[[], dict[str, Any]]
    load_runtime: Callable[[Path], _Runtime]
    sampler_factory: Callable[[Any, Callable[[], dict[str, int]]], Any]
    validate_bench_root: Callable[[str | Path], Path]
    runner_path: Path
    hash_randomization: int
    perf_counter_ns: Callable[[], int] = time.perf_counter_ns
    time_ns: Callable[[], int] = time.time_ns


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _resolved(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def _is_strict_descendant(path: Path, parent: Path) -> bool:
    return _path_key(path) != _path_key(parent) and parent.resolve() in path.resolve().parents


def _paths_overlap(left: Path, right: Path) -> bool:
    left_resolved = left.resolve()
    right_resolved = right.resolve()
    return (
        _path_key(left_resolved) == _path_key(right_resolved)
        or left_resolved in right_resolved.parents
        or right_resolved in left_resolved.parents
    )


def _same_existing_path(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return False
    try:
        return os.path.samefile(left, right)
    except OSError as exc:
        raise ValueError(f"Could not establish path identity for {left} and {right}") from exc


def _require_regular_file(path: Path, *, label: str) -> None:
    _require(path.exists(), f"{label} is missing: {path}")
    _require(not path.is_symlink(), f"{label} must not be a symlink: {path}")
    try:
        file_stat = path.stat(follow_symlinks=False)
        mode = file_stat.st_mode
    except OSError as exc:
        raise ValueError(f"Could not stat {label}: {path}") from exc
    _require(stat.S_ISREG(mode), f"{label} must be a regular file: {path}")
    _require(int(file_stat.st_nlink) == 1, f"{label} must not be hard-linked: {path}")


def _require_directory(path: Path, *, label: str) -> None:
    _require(path.exists(), f"{label} is missing: {path}")
    _require(not path.is_symlink(), f"{label} must not be a symlink: {path}")
    _require(path.is_dir(), f"{label} is not a directory: {path}")
    attributes = int(getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0))
    _require(not attributes & _WINDOWS_REPARSE_ATTRIBUTE, f"{label} must not be a reparse point: {path}")


def _require_empty_directory(path: Path, *, label: str) -> None:
    _require_directory(path, label=label)
    try:
        first = next(path.iterdir(), None)
    except OSError as exc:
        raise ValueError(f"Could not inspect {label}: {path}") from exc
    _require(first is None, f"{label} must be empty: {path}")


def _normalize_sha256(value: str, *, label: str) -> str:
    text = str(value).strip().lower()
    _require(_SHA256_RE.fullmatch(text) is not None, f"{label} must be a full SHA-256 digest")
    return text


def _normalize_head(value: str, *, label: str) -> str:
    text = str(value).strip().lower()
    _require(_HEX_HEAD_RE.fullmatch(text) is not None, f"{label} must be a full exact Git HEAD")
    return text


def _load_manifest(
    path: Path,
    *,
    validate_bench_root: Callable[[str | Path], Path],
) -> _ManifestContext:
    raw_manifest_path = Path(path).expanduser()
    _require(raw_manifest_path.is_absolute(), "Issue #116 preflight manifest path must be absolute")
    _require_regular_file(raw_manifest_path, label="Issue #116 preflight manifest")
    manifest_path = raw_manifest_path.resolve()
    _require(
        os.path.normcase(os.path.normpath(str(raw_manifest_path)))
        == os.path.normcase(os.path.normpath(str(manifest_path))),
        "Issue #116 preflight manifest path must be canonical and non-reparse",
    )
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read Issue #116 preflight manifest: {manifest_path}") from exc
    _require(isinstance(raw, dict), "Issue #116 preflight manifest must be a JSON object")
    _require(set(raw) == _EXPECTED_MANIFEST_KEYS, "Issue #116 preflight manifest top-level schema drifted")

    target = raw["target_worktree"]
    tool = raw["preflight_tool"]
    paths_raw = raw["paths"]
    environment = raw["environment"]
    _require(isinstance(target, dict) and set(target) == _EXPECTED_OWNER_KEYS, "Invalid target_worktree schema")
    _require(isinstance(tool, dict) and set(tool) == _EXPECTED_OWNER_KEYS, "Invalid preflight_tool schema")
    _require(isinstance(paths_raw, dict) and set(paths_raw) == _EXPECTED_PATH_KEYS, "Invalid paths schema")
    _require(isinstance(environment, dict) and set(environment) == _EXPECTED_ENV_KEYS, "Invalid environment schema")
    _require(all(isinstance(value, str) and value for value in paths_raw.values()), "Manifest paths must be strings")
    _require(all(isinstance(value, str) and value for value in environment.values()), "Manifest environment must be strings")

    for label, value in paths_raw.items():
        _require(Path(value).is_absolute(), f"Manifest {label} must be absolute")
        _require(
            os.path.normcase(os.path.normpath(str(Path(value))))
            == os.path.normcase(os.path.normpath(str(Path(value).resolve()))),
            f"Manifest {label} must be canonical and non-reparse",
        )
    bench_root = validate_bench_root(paths_raw["bench_root"])
    paths = _ManifestPaths(
        **{
            key: bench_root if key == "bench_root" else _resolved(value)
            for key, value in paths_raw.items()
        }
    )
    _require(_path_key(paths.preflight_manifest_path) == _path_key(manifest_path), "Manifest path does not name itself")
    _require(str(target["root"]) == str(paths.worktree_root), "Target root disagrees with manifest paths")
    _require(str(tool["root"]) == str(paths.preflight_tool_root), "Tool root disagrees with manifest paths")
    _require(str(raw["git_head"]) == str(target["git_head"]), "Legacy git_head disagrees with target HEAD")
    target_head = _normalize_head(str(target["git_head"]), label="target HEAD")
    tool_head = _normalize_head(str(tool["git_head"]), label="preflight-tool HEAD")

    _require_directory(paths.worktree_root, label="target worktree")
    _require_directory(paths.preflight_tool_root, label="preflight-tool worktree")
    _require_directory(paths.git_common_dir, label="Git common directory")
    _require_directory(paths.primary_worktree_root, label="primary worktree")
    _require_directory(paths.run_root, label="Issue #116 run root")
    for label, child in (
        ("target worktree", paths.worktree_root),
        ("preflight-tool worktree", paths.preflight_tool_root),
        ("run root", paths.run_root),
    ):
        _require(child.parent == paths.bench_root, f"{label} must be a direct child of {paths.bench_root}")
    for field in ("fg_response_cache_dir", "timeline_cache_dir", "optimizer_bin_dir", "artifacts_dir"):
        _require_directory(getattr(paths, field), label=field)
    _require(
        _path_key(paths.git_common_dir) == _path_key(paths.primary_worktree_root / ".git"),
        "Git common directory does not belong to the primary worktree",
    )
    _require(
        _path_key(paths.production_fg_cache_dir)
        == _path_key(paths.primary_worktree_root / "bin" / "fg_response_frontier_cache"),
        "Production FG cache ownership disagrees with the primary worktree",
    )

    isolated = (
        paths.fg_response_cache_dir,
        paths.timeline_cache_dir,
        paths.optimizer_bin_dir,
        paths.database_path,
        paths.profile_events_path,
        paths.artifacts_dir,
        paths.preflight_manifest_path,
    )
    for value in isolated:
        _require(_is_strict_descendant(value, paths.run_root), f"Isolated path escapes run root: {value}")
        _require(not _paths_overlap(value, paths.production_fg_cache_dir), f"Isolated path aliases production cache: {value}")
        _require(not _same_existing_path(value, paths.production_fg_cache_dir), f"Isolated path aliases production cache: {value}")
    for index, left in enumerate(isolated):
        for right in isolated[index + 1 :]:
            _require(not _paths_overlap(left, right), f"Manifest isolation paths overlap: {left} and {right}")
            _require(not _same_existing_path(left, right), f"Manifest isolation paths alias: {left} and {right}")
    for owner in (paths.worktree_root, paths.preflight_tool_root):
        _require(not _paths_overlap(owner, paths.run_root), f"Worktree overlaps run root: {owner}")

    for env_name, path_field in _ENV_PATH_FIELDS.items():
        expected = str(getattr(paths, path_field))
        _require(environment[env_name] == expected, f"Manifest environment disagrees for {env_name}")

    _require_empty_directory(paths.fg_response_cache_dir, label="isolated FG response cache")
    _require_empty_directory(paths.timeline_cache_dir, label="isolated timeline cache")
    _require_empty_directory(paths.optimizer_bin_dir, label="isolated optimizer bin")
    _require(not paths.database_path.exists(), f"Isolated database already exists: {paths.database_path}")
    _require(not paths.profile_events_path.exists(), f"Profile events already exist: {paths.profile_events_path}")
    _require(not (paths.artifacts_dir / _COMPLETED_REPORT_NAME).exists(), "Completed report already exists")
    _require(not (paths.artifacts_dir / _FAILURE_REPORT_NAME).exists(), "Failure report already exists")
    _require(
        not (paths.artifacts_dir / f"{_COMPLETED_REPORT_NAME}.tmp").exists(),
        "Completed-report temporary already exists",
    )
    _require(
        not (paths.artifacts_dir / f"{_FAILURE_REPORT_NAME}.tmp").exists(),
        "Failure-report temporary already exists",
    )
    return _ManifestContext(
        paths=paths,
        target_head=target_head,
        tool_head=tool_head,
        environment={str(key): str(value) for key, value in environment.items()},
    )


def _apply_and_validate_environment(
    context: _ManifestContext,
    *,
    hash_randomization: int,
) -> dict[str, str]:
    _require(
        "METAFINDER_CONFIG_PATH" not in os.environ,
        "METAFINDER_CONFIG_PATH must be absent before the runner pins target/config.ini",
    )
    for name, value in context.environment.items():
        if name in os.environ:
            _require(
                os.environ[name] == value,
                f"Inherited {name} disagrees with the preflight manifest",
            )
        os.environ[name] = value
    os.environ["METAFINDER_CONFIG_PATH"] = str(context.paths.worktree_root / "config.ini")

    _require(os.environ.get("PYTHONHASHSEED") == "0", "PYTHONHASHSEED=0 must be set before interpreter launch")
    _require(int(hash_randomization) == 0, "Interpreter hash randomization proves PYTHONHASHSEED=0 was not active at launch")
    pycache_raw = str(os.environ.get("PYTHONPYCACHEPREFIX") or "").strip()
    numba_raw = str(os.environ.get("NUMBA_CACHE_DIR") or "").strip()
    _require(pycache_raw, "PYTHONPYCACHEPREFIX must be configured before interpreter launch")
    _require(numba_raw, "NUMBA_CACHE_DIR must be configured before target imports")
    _require(Path(pycache_raw).is_absolute(), "PYTHONPYCACHEPREFIX must be absolute")
    _require(Path(numba_raw).is_absolute(), "NUMBA_CACHE_DIR must be absolute")
    pycache = _resolved(pycache_raw)
    numba_cache = _resolved(numba_raw)
    _require(
        os.path.normcase(os.path.normpath(pycache_raw)) == os.path.normcase(os.path.normpath(str(pycache))),
        "PYTHONPYCACHEPREFIX must be canonical and non-reparse",
    )
    _require(
        os.path.normcase(os.path.normpath(numba_raw))
        == os.path.normcase(os.path.normpath(str(numba_cache))),
        "NUMBA_CACHE_DIR must be canonical and non-reparse",
    )
    _require(_is_strict_descendant(pycache, context.paths.artifacts_dir), "PYTHONPYCACHEPREFIX must be inside artifacts")
    _require(_is_strict_descendant(numba_cache, context.paths.artifacts_dir), "NUMBA_CACHE_DIR must be inside artifacts")
    _require(not _paths_overlap(pycache, numba_cache), "Python and Numba cache paths overlap")
    for reserved in (
        context.paths.artifacts_dir / _COMPLETED_REPORT_NAME,
        context.paths.artifacts_dir / _FAILURE_REPORT_NAME,
    ):
        _require(not _paths_overlap(pycache, reserved), f"Python cache path overlaps reserved report: {reserved}")
        _require(not _paths_overlap(numba_cache, reserved), f"Numba cache path overlaps reserved report: {reserved}")
    _require(sys.pycache_prefix is not None, "PYTHONPYCACHEPREFIX was not active at interpreter startup")
    _require(_path_key(_resolved(sys.pycache_prefix)) == _path_key(pycache), "sys.pycache_prefix disagrees with environment")
    if numba_cache.exists():
        _require_empty_directory(numba_cache, label="isolated Numba cache")
    else:
        numba_cache.mkdir(parents=False, exist_ok=False)
    recorded_names = {
        key
        for key in os.environ
        if key in _RECORDED_ENV_KEYS
        or key.upper().startswith(("NUMBA_", "OMP_", "MKL_", "OPENBLAS_", "VECLIB_", "BLIS_"))
    }
    return {key: str(os.environ[key]) for key in sorted(recorded_names)}


def _git_environment() -> dict[str, str]:
    overrides = sorted(key for key in os.environ if key.upper().startswith("GIT_"))
    _require(not overrides, f"Git environment overrides are forbidden: {overrides}")
    return dict(os.environ)


def _run_git(root: Path, args: Sequence[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *[str(arg) for arg in args]],
            check=True,
            capture_output=True,
            text=True,
            env=_git_environment(),
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"Git command failed in {root}: {' '.join(args)}") from exc
    return str(result.stdout).strip()


def _git_state(
    root: Path,
    expected_head: str,
    *,
    expected_common_dir: Path,
    expected_primary_root: Path,
    run_git: Callable[[Path, Sequence[str]], str],
) -> _GitState:
    top_level = _resolved(
        run_git(root, ("rev-parse", "--path-format=absolute", "--show-toplevel"))
    )
    common_dir = _resolved(
        run_git(root, ("rev-parse", "--path-format=absolute", "--git-common-dir"))
    )
    _require(_path_key(top_level) == _path_key(root), f"Git top-level disagrees for {root}")
    _require(
        _path_key(common_dir) == _path_key(expected_common_dir),
        f"Git common directory disagrees for {root}",
    )
    worktree_output = run_git(root, ("worktree", "list", "--porcelain"))
    registered = tuple(
        _resolved(line.removeprefix("worktree ").strip())
        for line in worktree_output.splitlines()
        if line.startswith("worktree ")
    )
    _require(bool(registered), f"Git reported no registered worktrees for {root}")
    _require(_path_key(registered[0]) == _path_key(expected_primary_root), "Git primary worktree disagrees")
    _require(any(_path_key(value) == _path_key(root) for value in registered), f"Git worktree is unregistered: {root}")
    first = _normalize_head(run_git(root, ("rev-parse", "HEAD")), label=f"HEAD for {root}")
    status_text = run_git(root, ("status", "--porcelain", "--untracked-files=all"))
    second = _normalize_head(run_git(root, ("rev-parse", "HEAD")), label=f"HEAD for {root}")
    _require(first == second, f"Git HEAD changed while reading status: {root}")
    _require(first == expected_head, f"Git HEAD disagrees with preflight manifest: {root}")
    _require(not status_text.strip(), f"Git worktree is not clean: {root}: {status_text.strip()}")
    return _GitState(root=root, head=first, status="")


def _sha256_file(path: Path) -> _HashedFile:
    _require_regular_file(path, label="hashed file")
    before = path.stat(follow_symlinks=False)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(8 * 1024 * 1024)
            if not block:
                break
            digest.update(block)
    after = path.stat(follow_symlinks=False)
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    _require(identity_before == identity_after, f"File mutated while hashing: {path}")
    return _HashedFile(
        path=path,
        sha256=digest.hexdigest(),
        size=int(after.st_size),
        mtime_ns=int(after.st_mtime_ns),
        device=int(after.st_dev),
        inode=int(after.st_ino),
    )


def _relative_tracked_path(root: Path, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"Tracked input escapes its worktree: {path}") from exc
    _require(relative.parts and ".." not in relative.parts, f"Invalid tracked input path: {path}")
    return relative.as_posix()


def _tracked_input_snapshot(
    root: Path,
    path: Path,
    *,
    expected_sha256: str | None,
    run_git: Callable[[Path, Sequence[str]], str],
) -> _InputSnapshot:
    file_path = path.resolve()
    _require_regular_file(file_path, label="tracked input")
    relative = _relative_tracked_path(root, file_path)
    stage = run_git(root, ("ls-files", "--stage", "--", relative))
    stage_lines = [line for line in stage.splitlines() if line.strip()]
    _require(len(stage_lines) == 1, f"Input is not one tracked stage-0 file: {relative}")
    try:
        stage_header, stage_path = stage_lines[0].split("\t", 1)
        mode, index_blob, stage_number = stage_header.split()
    except ValueError as exc:
        raise ValueError(f"Could not parse Git index entry for {relative}") from exc
    _require(stage_path.replace("\\", "/") == relative, f"Git index path disagrees for {relative}")
    _require(stage_number == "0" and mode in {"100644", "100755"}, f"Input is not a regular stage-0 file: {relative}")
    committed_blob = run_git(root, ("rev-parse", f"HEAD:{relative}")).strip().lower()
    worktree_blob = run_git(root, ("hash-object", "--", relative)).strip().lower()
    index_blob = index_blob.strip().lower()
    _require(_HEX_HEAD_RE.fullmatch(index_blob) is not None, f"Invalid Git blob for {relative}")
    _require(index_blob == committed_blob == worktree_blob, f"Tracked input blob drifted for {relative}")
    hashed = _sha256_file(file_path)
    if expected_sha256 is not None:
        _require(hashed.sha256 == expected_sha256, f"SHA-256 mismatch for {relative}")
    return _InputSnapshot(
        path=file_path,
        relative_path=relative,
        sha256=hashed.sha256,
        git_blob=index_blob,
        size=hashed.size,
        mtime_ns=hashed.mtime_ns,
        device=hashed.device,
        inode=hashed.inode,
    )


class _PerformanceInformation(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("CommitTotal", ctypes.c_size_t),
        ("CommitLimit", ctypes.c_size_t),
        ("CommitPeak", ctypes.c_size_t),
        ("PhysicalTotal", ctypes.c_size_t),
        ("PhysicalAvailable", ctypes.c_size_t),
        ("SystemCache", ctypes.c_size_t),
        ("KernelTotal", ctypes.c_size_t),
        ("KernelPaged", ctypes.c_size_t),
        ("KernelNonpaged", ctypes.c_size_t),
        ("PageSize", ctypes.c_size_t),
        ("HandleCount", ctypes.c_ulong),
        ("ProcessCount", ctypes.c_ulong),
        ("ThreadCount", ctypes.c_ulong),
    ]


def _windows_capacity_snapshot() -> dict[str, int]:
    _require(platform.system() == "Windows", "Issue #116 corpus runner requires Windows")
    try:
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        function = psapi.GetPerformanceInfo
        function.argtypes = (ctypes.POINTER(_PerformanceInformation), ctypes.c_ulong)
        function.restype = ctypes.c_int
        info = _PerformanceInformation()
        info.cb = ctypes.sizeof(info)
        if not function(ctypes.byref(info), info.cb):
            raise ctypes.WinError(ctypes.get_last_error())
    except (AttributeError, OSError) as exc:
        raise ValueError("Could not read Windows system commit capacity") from exc
    page_size = int(info.PageSize)
    commit_total = int(info.CommitTotal) * page_size
    commit_limit = int(info.CommitLimit) * page_size
    return {
        "page_size_bytes": page_size,
        "commit_total_bytes": commit_total,
        "commit_limit_bytes": commit_limit,
        "commit_peak_bytes": int(info.CommitPeak) * page_size,
        "commit_available_bytes": commit_limit - commit_total,
        "physical_total_bytes": int(info.PhysicalTotal) * page_size,
        "physical_available_bytes": int(info.PhysicalAvailable) * page_size,
    }


def _validate_live_bench_root(value: str | Path) -> Path:
    _require(platform.system() == "Windows", "Issue #116 corpus runner requires Windows")
    text = str(value)
    _require(text == str(_FIXED_BENCH_ROOT), f"Issue #116 bench root must be exactly {_FIXED_BENCH_ROOT}")
    absolute = Path(os.path.abspath(text))
    _require(str(absolute) == str(_FIXED_BENCH_ROOT), "Issue #116 bench root is not canonical")
    _require_directory(absolute, label="fixed Issue #116 bench root")
    _require(absolute.resolve() == absolute, "Issue #116 bench root resolves through an alias")
    return absolute


def _validate_capacity(snapshot: Mapping[str, int]) -> dict[str, int]:
    required = {
        "page_size_bytes",
        "commit_total_bytes",
        "commit_limit_bytes",
        "commit_peak_bytes",
        "commit_available_bytes",
        "physical_total_bytes",
        "physical_available_bytes",
    }
    _require(set(snapshot) == required, "Capacity snapshot schema drifted")
    normalized = {key: int(value) for key, value in snapshot.items()}
    _require(normalized["page_size_bytes"] > 0, "Windows page size is invalid")
    _require(all(value >= 0 for value in normalized.values()), "Windows capacity snapshot contains a negative value")
    _require(normalized["commit_total_bytes"] <= normalized["commit_limit_bytes"], "Commit total exceeds limit")
    _require(
        normalized["commit_available_bytes"]
        == normalized["commit_limit_bytes"] - normalized["commit_total_bytes"],
        "Windows commit-availability accounting is incoherent",
    )
    _require(
        normalized["physical_available_bytes"] <= normalized["physical_total_bytes"],
        "Windows physical-availability accounting is incoherent",
    )
    _require(
        normalized["commit_available_bytes"] >= _REQUIRED_HEADROOM_BYTES,
        "Insufficient Windows commit headroom for one Issue #116 build",
    )
    _require(
        normalized["physical_available_bytes"] >= _REQUIRED_HEADROOM_BYTES,
        "Insufficient physical-memory headroom for one Issue #116 build",
    )
    return normalized


def _run_json_powershell(script: str) -> Any:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=20.0,
        )
        return json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise ValueError("Could not collect required Windows hardware metadata") from exc


def _windows_hardware_snapshot() -> dict[str, Any]:
    _require(platform.system() == "Windows", "Issue #116 corpus runner requires Windows")
    script = r"""
$ErrorActionPreference = 'Stop'
[pscustomobject]@{
  cpu = @(Get-CimInstance Win32_Processor | Select-Object Name,Manufacturer,ProcessorId,NumberOfCores,NumberOfLogicalProcessors)
  gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name,PNPDeviceID,DriverVersion,AdapterRAM)
  os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,TotalVisibleMemorySize,TotalVirtualMemorySize
} | ConvertTo-Json -Depth 5 -Compress
"""
    data = _run_json_powershell(script)
    _require(isinstance(data, dict), "Windows hardware metadata was not an object")
    cpu = data.get("cpu")
    gpu = data.get("gpu")
    if isinstance(cpu, dict):
        cpu = [cpu]
    if isinstance(gpu, dict):
        gpu = [gpu]
    _require(isinstance(cpu, list) and cpu, "Windows CPU metadata is missing")
    _require(isinstance(gpu, list) and gpu, "Windows GPU metadata is missing")
    try:
        power = subprocess.run(
            ["powercfg", "/getactivescheme"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10.0,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Could not collect active Windows power scheme") from exc
    _require(bool(power), "Windows active power scheme is missing")
    return {
        "platform": platform.platform(),
        "python": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "logical_cpu_count": int(os.cpu_count() or 0),
        "cpu": cpu,
        "gpu": gpu,
        "os": data.get("os"),
        "active_power_scheme": power,
    }


def _load_live_runtime(target_root: Path) -> _Runtime:
    contaminated = sorted(
        name
        for name in sys.modules
        if name in {"numpy", "numba", "psutil", "gear_optimizer"}
        or name.startswith(("numpy.", "numba.", "psutil.", "gear_optimizer."))
    )
    _require(not contaminated, f"Target runtime was imported before validation: {contaminated[:5]}")
    sys.path.insert(0, str(target_root))
    importlib.invalidate_caches()

    np = importlib.import_module("numpy")
    numba = importlib.import_module("numba")
    psutil = importlib.import_module("psutil")
    csv_parser = importlib.import_module("gear_optimizer.data.csv_parser")
    song_io = importlib.import_module("gear_optimizer.data.song_io")
    ref_builder = importlib.import_module("gear_optimizer.helpers.song_helpers.ref_array_builder")
    prebuild = importlib.import_module("gear_optimizer.solver.fg_response_frontier_cache_prebuild")
    reducer = importlib.import_module(
        "gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_reducer"
    )
    cache_types = importlib.import_module(
        "gear_optimizer.solver.taichi_gem.force_greats.response_cache_types"
    )
    constants = importlib.import_module("gear_optimizer.core.constants")
    config = importlib.import_module("gear_optimizer.core.config")

    target = target_root.resolve()
    wrong_owner: list[str] = []
    for name, module in tuple(sys.modules.items()):
        if name != "gear_optimizer" and not name.startswith("gear_optimizer."):
            continue
        file_name = getattr(module, "__file__", None)
        if not file_name or not _is_strict_descendant(Path(file_name).resolve(), target):
            wrong_owner.append(name)
    _require(not wrong_owner, f"gear_optimizer imports escaped target worktree: {wrong_owner[:5]}")
    for label, module in (("NumPy", np), ("Numba", numba), ("psutil", psutil)):
        module_file = Path(str(getattr(module, "__file__", ""))).resolve()
        _require(module_file.is_file(), f"{label} module ownership is unavailable")
        _require(
            not _is_strict_descendant(module_file, target),
            f"{label} was shadowed by the target worktree",
        )
    return _Runtime(
        np=np,
        numba=numba,
        psutil=psutil,
        read_table=csv_parser.read_table,
        get_base_calc_song=song_io.get_base_calc_song,
        build_ref_arrays_from_stats=ref_builder.build_ref_arrays_from_stats,
        prebuild=prebuild,
        reducer=reducer,
        cache_types=cache_types,
        constants=constants,
        config=config,
    )


def _memory_info(process: Any) -> dict[str, int]:
    info = process.memory_info()
    fields = ("rss", "wset", "private", "peak_wset", "peak_pagefile")
    missing = [name for name in fields if not hasattr(info, name)]
    _require(not missing, f"Windows process memory fields are missing: {missing}")
    return {name: int(getattr(info, name)) for name in fields}


class _MemorySampler:
    def __init__(self, psutil_module: Any, capacity_reader: Callable[[], dict[str, int]]) -> None:
        self._psutil = psutil_module
        self._capacity_reader = capacity_reader
        self._process = psutil_module.Process()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="issue116-memory-sampler", daemon=True)
        self._errors: list[str] = []
        self._samples = 0
        self._max_process = {"rss": 0, "wset": 0, "private": 0}
        self._max_commit_total = 0
        self._min_commit_available: int | None = None
        self._min_physical_available: int | None = None

    def _take(self) -> None:
        memory = _memory_info(self._process)
        capacity = _validate_capacity_schema_only(self._capacity_reader())
        for name in self._max_process:
            self._max_process[name] = max(self._max_process[name], int(memory[name]))
        self._max_commit_total = max(self._max_commit_total, int(capacity["commit_total_bytes"]))
        commit_available = int(capacity["commit_available_bytes"])
        physical_available = int(capacity["physical_available_bytes"])
        self._min_commit_available = (
            commit_available
            if self._min_commit_available is None
            else min(self._min_commit_available, commit_available)
        )
        self._min_physical_available = (
            physical_available
            if self._min_physical_available is None
            else min(self._min_physical_available, physical_available)
        )
        self._samples += 1

    def _run(self) -> None:
        while not self._stop.wait(_SAMPLE_INTERVAL_SECONDS):
            try:
                self._take()
            except Exception as exc:  # surfaced synchronously by report()
                self._errors.append(f"{type(exc).__name__}: {exc}")
                self._stop.set()

    def start(self) -> None:
        self._take()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=_SAMPLE_INTERVAL_SECONDS * 2.0)
        _require(not self._thread.is_alive(), "Memory sampler did not stop")
        self._take()

    def report(self) -> dict[str, Any]:
        _require(not self._errors, f"Memory sampler failed: {self._errors}")
        _require(self._samples >= 2, "Memory sampler did not capture start and completion")
        return {
            "interval_seconds": _SAMPLE_INTERVAL_SECONDS,
            "sample_count": int(self._samples),
            "max_process_bytes": dict(self._max_process),
            "max_system_commit_total_bytes": int(self._max_commit_total),
            "min_system_commit_available_bytes": int(self._min_commit_available or 0),
            "min_system_physical_available_bytes": int(self._min_physical_available or 0),
        }


def _validate_capacity_schema_only(snapshot: Mapping[str, int]) -> dict[str, int]:
    required = {
        "page_size_bytes",
        "commit_total_bytes",
        "commit_limit_bytes",
        "commit_peak_bytes",
        "commit_available_bytes",
        "physical_total_bytes",
        "physical_available_bytes",
    }
    _require(set(snapshot) == required, "Capacity snapshot schema drifted during sampling")
    normalized = {key: int(value) for key, value in snapshot.items()}
    _require(normalized["page_size_bytes"] > 0, "Sampled Windows page size is invalid")
    _require(all(value >= 0 for value in normalized.values()), "Sampled capacity contains a negative value")
    _require(
        normalized["commit_available_bytes"]
        == normalized["commit_limit_bytes"] - normalized["commit_total_bytes"],
        "Sampled Windows commit accounting is incoherent",
    )
    _require(
        normalized["physical_available_bytes"] <= normalized["physical_total_bytes"],
        "Sampled Windows physical accounting is incoherent",
    )
    return normalized


def _live_sampler_factory(psutil_module: Any, reader: Callable[[], dict[str, int]]) -> _MemorySampler:
    return _MemorySampler(psutil_module, reader)


def _ref_array_report(runtime: _Runtime, stats_path: Path) -> tuple[dict[str, Any], tuple[tuple[int, int], ...]]:
    np = runtime.np
    total_rows = int(runtime.constants.TOTAL_ROWS)
    _require(total_rows == 160, "Issue #116 runner requires the canonical 0..160 stat grid")
    stats_table = runtime.read_table(str(stats_path))
    _require(isinstance(stats_table, list) and len(stats_table) == total_rows + 1, "Stats table must have exactly 161 rows")
    for index, row in enumerate(stats_table):
        _require(isinstance(row, list) and len(row) == 5, f"Stats row {index} must have exactly five values")
        _require(all(math.isfinite(float(value)) for value in row), f"Stats row {index} contains a non-finite value")
    ref_arrays = runtime.build_ref_arrays_from_stats(stats_table, dtype=np.float32)
    expected_names = {
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    }
    _require(set(ref_arrays) == expected_names, "Reference-array schema drifted")
    array_report: dict[str, Any] = {}
    for name in sorted(expected_names):
        array = np.asarray(ref_arrays[name])
        _require(array.dtype == np.dtype(np.float32), f"{name} reference array is not float32")
        _require(array.shape == (total_rows + 1,), f"{name} reference array has the wrong shape")
        _require(bool(np.all(np.isfinite(array))), f"{name} reference array contains a non-finite value")
        contiguous = np.ascontiguousarray(array, dtype=np.float32)
        array_report[name] = {
            "dtype": str(contiguous.dtype),
            "shape": [int(value) for value in contiguous.shape],
            "sha256": hashlib.sha256(contiguous.tobytes(order="C")).hexdigest(),
        }
    keys = tuple(runtime.cache_types.all_response_stat_keys())
    _require(len(keys) == 25_921, "FG response stat-key grid is not 25,921 keys")
    _require(keys[0] == (0, 0) and keys[-1] == (160, 160), "FG response stat-key order drifted")
    _require(len(set(keys)) == len(keys), "FG response stat-key grid contains duplicates")
    key_rows = np.asarray(keys, dtype=np.int32)
    _require(key_rows.shape == (25_921, 2), "FG response stat-key array shape drifted")
    return {
        "arrays": array_report,
        "stat_key_count": len(keys),
        "stat_key_sha256": hashlib.sha256(np.ascontiguousarray(key_rows).tobytes(order="C")).hexdigest(),
        "ref_arrays": ref_arrays,
    }, keys


def _strict_metadata_int(metadata: Mapping[str, Any], key: str) -> int:
    value = str(metadata.get(key, "")).strip()
    _require(bool(re.fullmatch(r"[0-9]+", value)), f"Chart metadata {key} is not an integer")
    return int(value)


def _postparse_chart(runtime: _Runtime, chart_path: Path, expected_notes: int, expected_held: int) -> dict[str, Any]:
    np = runtime.np
    calc_song = runtime.get_base_calc_song(str(chart_path), {})
    _require(isinstance(calc_song, dict) and calc_song, "Canonical chart parser returned no song")
    song_data = calc_song.get("song_data")
    metadata = calc_song.get("metadata")
    _require(isinstance(song_data, dict) and isinstance(metadata, dict), "Canonical chart shape is invalid")
    timestamps = np.asarray(song_data.get("timestamps"), dtype=np.float32).reshape(-1)
    note_types = np.asarray(song_data.get("note_types"), dtype=np.int16).reshape(-1)
    lanes = np.asarray(song_data.get("lanes"), dtype=np.int32).reshape(-1)
    _require(timestamps.shape[0] == expected_notes, "Canonical parsed note count disagrees")
    _require(note_types.shape[0] == expected_notes, "Canonical note-type count disagrees")
    _require(lanes.shape[0] == expected_notes, "Canonical lane count disagrees")
    _require(bool(np.all(np.isfinite(timestamps))), "Canonical timestamps contain non-finite values")
    _require(bool(np.all(timestamps[1:] >= timestamps[:-1])), "Canonical timestamps are not sorted")
    _require(bool(np.all((lanes >= 1) & (lanes <= 4))), "Canonical lanes must remain in the chart's 1..4 range")
    unique_types = {int(value) for value in np.unique(note_types).tolist()}
    _require(unique_types.issubset({1, 2, 3}), f"Canonical note types are invalid: {sorted(unique_types)}")
    held_heads = int(np.count_nonzero(note_types == 2))
    held_tails = int(np.count_nonzero(note_types == 3))
    _require(held_heads == expected_held, "Canonical held-head count disagrees")
    _require(held_tails == expected_held, "Canonical held-tail count disagrees")
    _require(_strict_metadata_int(metadata, "Total Notes") == expected_notes, "Metadata Total Notes disagrees")
    _require(_strict_metadata_int(metadata, "Long Notes") == expected_held, "Metadata Long Notes disagrees")
    return {
        "note_count": int(expected_notes),
        "held_head_count": held_heads,
        "held_tail_count": held_tails,
        "metadata_total_notes": int(expected_notes),
        "metadata_long_notes": int(expected_held),
        "first_timestamp": float(timestamps[0]) if expected_notes else None,
        "last_timestamp": float(timestamps[-1]) if expected_notes else None,
    }


def _cache_outputs(
    runtime: _Runtime,
    context: _ManifestContext,
    result: Any,
    stat_keys: tuple[tuple[int, int], ...],
    *,
    expected_version: str,
    expected_notes: int,
    expected_held: int,
) -> dict[str, Any]:
    np = runtime.np
    _require(str(getattr(result, "source", "")) == "built", "FG cache result source was not built")
    build_ms = float(getattr(result, "build_ms", float("nan")))
    _require(math.isfinite(build_ms) and build_ms >= 0.0, "FG cache result build_ms is invalid")
    cache_file = _resolved(str(getattr(result, "cache_file", "")))
    _require(cache_file.parent == context.paths.fg_response_cache_dir, "Returned cache file escaped isolated FG cache")
    _require(cache_file.suffix == ".npz", "Returned cache file is not an NPZ bundle")
    stem = cache_file.stem
    pool = cache_file.with_name(f"{stem}.surf_pool.npy")
    coeffs = cache_file.with_name(f"{stem}.surf_coeffs.npy")
    expected_files = {cache_file, pool, coeffs}
    actual_entries = set(context.paths.fg_response_cache_dir.iterdir())
    _require(actual_entries == expected_files, "Isolated FG cache did not contain exactly one bundle and two sidecars")
    for path in expected_files:
        _require_regular_file(path, label="FG cache output")
    with np.load(cache_file, allow_pickle=False) as payload:
        persisted_version = str(np.asarray(payload["version"]).item())
        persisted_keys = np.asarray(payload["stat_keys"], dtype=np.int32)
        persisted_notes = int(np.asarray(payload["total_notes"]).item())
        persisted_held = int(np.asarray(payload["long_notes"]).item())
    _require(persisted_version == expected_version, "Persisted FG cache version disagrees")
    _require(persisted_keys.shape == (25_921, 2), "Persisted stat-key shape disagrees")
    _require(bool(np.array_equal(persisted_keys, np.asarray(stat_keys, dtype=np.int32))), "Persisted stat keys disagree")
    _require(persisted_notes == expected_notes, "Persisted note count disagrees")
    _require(persisted_held == expected_held, "Persisted held count disagrees")
    hashed = [_sha256_file(path) for path in sorted(expected_files, key=lambda item: item.name)]
    return {
        "cache_file": str(cache_file),
        "source": "built",
        "build_ms": build_ms,
        "version": persisted_version,
        "files": [asdict(value) | {"path": str(value.path)} for value in hashed],
        "_hashed": hashed,
    }


def _profile_events(path: Path, *, chart_name: str, expected_notes: int) -> dict[str, Any]:
    hashed = _sha256_file(path)
    events: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                _require(bool(line.strip()), f"Profile event line {line_number} is empty")
                event = json.loads(line)
                _require(isinstance(event, dict), f"Profile event line {line_number} is not an object")
                events.append(event)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not parse profile events: {path}") from exc
    _require(events, "Profile events file is empty")
    completed = [
        event
        for event in events
        if event.get("component") == "fg_response_cache" and event.get("event") == "prebuild_song_done"
    ]
    _require(len(completed) == 1, "Expected exactly one FG prebuild_song_done profile event")
    done = completed[0]
    metrics = done.get("metrics")
    _require(isinstance(metrics, dict), "FG prebuild completion event has no metrics")
    _require(str(metrics.get("source")) == "built", "FG completion profile source was not built")
    _require(int(metrics.get("note_count", -1)) == expected_notes, "FG completion profile note count disagrees")
    _require(str(done.get("song_key")) == chart_name, "FG completion profile chart name disagrees")
    counts = Counter((str(event.get("component", "")), str(event.get("event", ""))) for event in events)
    return {
        "path": str(path),
        "sha256": hashed.sha256,
        "size": hashed.size,
        "line_count": len(events),
        "event_counts": {
            f"{component}/{event}": count for (component, event), count in sorted(counts.items())
        },
        "_hashed": hashed,
    }


def _assert_hashed_file_unchanged(value: _HashedFile) -> None:
    current = value.path.stat(follow_symlinks=False)
    expected = (value.device, value.inode, value.size, value.mtime_ns)
    actual = (int(current.st_dev), int(current.st_ino), int(current.st_size), int(current.st_mtime_ns))
    _require(actual == expected, f"Hashed file changed before report publication: {value.path}")


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    output = path.resolve()
    _require(not output.exists(), f"JSON output already exists: {output}")
    _require_directory(output.parent, label="JSON output parent")
    temporary = output.with_name(f"{output.name}.tmp")
    _require(not temporary.exists(), f"JSON temporary output already exists: {temporary}")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, allow_nan=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        _require(not output.exists(), f"JSON output appeared during publication: {output}")
        os.replace(temporary, output)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _snapshot_report(value: _InputSnapshot) -> dict[str, Any]:
    report = asdict(value)
    report["path"] = str(value.path)
    return report


def _git_report(value: _GitState) -> dict[str, Any]:
    return {"root": str(value.root), "head": value.head, "status": value.status}


def _parse_chart_path(target_root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    _require(not relative.is_absolute(), "Chart path must be relative to the target worktree")
    _require(relative.parts and ".." not in relative.parts, "Chart path must not traverse parents")
    chart = (target_root / relative).resolve()
    _require(_is_strict_descendant(chart, target_root), "Chart path escapes the target worktree")
    return chart


def _execute(args: argparse.Namespace, context: _ManifestContext, deps: _Dependencies) -> dict[str, Any]:
    _require(_path_key(Path.cwd()) == _path_key(context.paths.worktree_root), "Current directory must be the target worktree root")
    environment_report = _apply_and_validate_environment(
        context,
        hash_randomization=deps.hash_randomization,
    )
    _git_environment()

    pre_capacity = _validate_capacity(deps.read_capacity())
    hardware = deps.read_hardware()
    _require(isinstance(hardware, dict) and hardware, "Hardware metadata is missing")

    target_pre = _git_state(
        context.paths.worktree_root,
        context.target_head,
        expected_common_dir=context.paths.git_common_dir,
        expected_primary_root=context.paths.primary_worktree_root,
        run_git=deps.run_git,
    )
    tool_pre = (
        target_pre
        if context.paths.preflight_tool_root == context.paths.worktree_root
        else _git_state(
            context.paths.preflight_tool_root,
            context.tool_head,
            expected_common_dir=context.paths.git_common_dir,
            expected_primary_root=context.paths.primary_worktree_root,
            run_git=deps.run_git,
        )
    )
    if tool_pre is target_pre:
        _require(context.tool_head == context.target_head, "Same target/tool worktree has different manifest HEADs")

    expected_chart_sha = _normalize_sha256(args.expected_chart_sha256, label="chart SHA-256")
    expected_stats_sha = _normalize_sha256(args.expected_stats_sha256, label="Stats SHA-256")
    expected_config_sha = _normalize_sha256(args.expected_config_sha256, label="config SHA-256")
    expected_notes = int(args.expected_note_count)
    expected_held = int(args.expected_held_count)
    _require(expected_notes > 0, "Expected note count must be positive")
    _require(0 <= expected_held <= expected_notes, "Expected held count is invalid")
    expected_version = str(args.expected_cache_version).strip()
    _require(bool(expected_version), "Expected cache version is required")

    chart_path = _parse_chart_path(context.paths.worktree_root, args.chart_relative)
    stats_path = (context.paths.worktree_root / "Data" / "Gear" / "Stats.txt").resolve()
    config_path = (context.paths.worktree_root / "config.ini").resolve()
    chart_pre = _tracked_input_snapshot(
        context.paths.worktree_root,
        chart_path,
        expected_sha256=expected_chart_sha,
        run_git=deps.run_git,
    )
    stats_pre = _tracked_input_snapshot(
        context.paths.worktree_root,
        stats_path,
        expected_sha256=expected_stats_sha,
        run_git=deps.run_git,
    )
    config_pre = _tracked_input_snapshot(
        context.paths.worktree_root,
        config_path,
        expected_sha256=expected_config_sha,
        run_git=deps.run_git,
    )
    runner_pre = _tracked_input_snapshot(
        context.paths.preflight_tool_root,
        deps.runner_path.resolve(),
        expected_sha256=None,
        run_git=deps.run_git,
    )
    input_paths = (chart_pre.path, stats_pre.path, config_pre.path, runner_pre.path)
    for index, left in enumerate(input_paths):
        for right in input_paths[index + 1 :]:
            _require(not _same_existing_path(left, right), f"Tracked inputs alias: {left} and {right}")

    runtime = deps.load_runtime(context.paths.worktree_root)
    _require(
        _path_key(_resolved(runtime.config.get_config_path())) == _path_key(config_path),
        "Effective config loader path disagrees with tracked target/config.ini",
    )
    _require(
        float(runtime.prebuild._FG_PREBUILD_PEAK_COMMIT_GB) == 7.0
        and float(runtime.prebuild._FG_PREBUILD_SYSTEM_RESERVE_GB) == 6.0,
        "Production FG capacity anchors drifted from the ratified 13 GB reservation",
    )
    runtime_version = str(runtime.cache_types._FG_RESPONSE_CACHE_VERSION)
    _require(runtime_version == expected_version, "Target FG cache version disagrees with expected version")
    refs, stat_keys = _ref_array_report(runtime, stats_path)
    ref_arrays = refs.pop("ref_arrays")
    runtime.reducer.configure_force_greats_response_first_frontier_threads(2)
    effective_threads = int(runtime.reducer._resolve_first_only_reducer_threads(len(stat_keys)))
    _require(effective_threads == 2, "FG reducer thread count was not pinned to two")

    capacity_at_build_entry = _validate_capacity(deps.read_capacity())
    process = runtime.psutil.Process()
    process_before = _memory_info(process)
    virtual_before = runtime.psutil.virtual_memory()
    swap_before = runtime.psutil.swap_memory()
    sampler = deps.sampler_factory(runtime.psutil, deps.read_capacity)
    sampler.start()
    started_wall_ns = int(deps.time_ns())
    started_perf_ns = int(deps.perf_counter_ns())
    try:
        result = runtime.prebuild.build_fg_response_frontier_cache_for_path(
            str(chart_path),
            ref_arrays,
            stat_keys=stat_keys,
        )
        ended_perf_ns = int(deps.perf_counter_ns())
        process_at_completed_return = _memory_info(process)
        ended_wall_ns = int(deps.time_ns())
    except Exception:
        sampler.stop()
        raise
    sampler.stop()
    sampled_memory = sampler.report()
    wall_ms = float(ended_perf_ns - started_perf_ns) / 1_000_000.0
    _require(math.isfinite(wall_ms) and wall_ms >= 0.0, "Measured wall time is invalid")

    chart_report = _postparse_chart(runtime, chart_path, expected_notes, expected_held)
    cache_report = _cache_outputs(
        runtime,
        context,
        result,
        stat_keys,
        expected_version=expected_version,
        expected_notes=expected_notes,
        expected_held=expected_held,
    )
    _require(_path_key(_resolved(str(getattr(result, "path", "")))) == _path_key(chart_path), "Build result chart path disagrees")
    profile_report = _profile_events(
        context.paths.profile_events_path,
        chart_name=chart_path.name,
        expected_notes=expected_notes,
    )
    _require(not context.paths.database_path.exists(), "Direct FG build unexpectedly created the isolated database")
    _require_empty_directory(context.paths.timeline_cache_dir, label="isolated timeline cache after build")
    _require_empty_directory(context.paths.optimizer_bin_dir, label="isolated optimizer bin after build")

    target_post = _git_state(
        context.paths.worktree_root,
        context.target_head,
        expected_common_dir=context.paths.git_common_dir,
        expected_primary_root=context.paths.primary_worktree_root,
        run_git=deps.run_git,
    )
    tool_post = (
        target_post
        if context.paths.preflight_tool_root == context.paths.worktree_root
        else _git_state(
            context.paths.preflight_tool_root,
            context.tool_head,
            expected_common_dir=context.paths.git_common_dir,
            expected_primary_root=context.paths.primary_worktree_root,
            run_git=deps.run_git,
        )
    )
    chart_post = _tracked_input_snapshot(
        context.paths.worktree_root,
        chart_path,
        expected_sha256=expected_chart_sha,
        run_git=deps.run_git,
    )
    stats_post = _tracked_input_snapshot(
        context.paths.worktree_root,
        stats_path,
        expected_sha256=expected_stats_sha,
        run_git=deps.run_git,
    )
    config_post = _tracked_input_snapshot(
        context.paths.worktree_root,
        config_path,
        expected_sha256=expected_config_sha,
        run_git=deps.run_git,
    )
    runner_post = _tracked_input_snapshot(
        context.paths.preflight_tool_root,
        deps.runner_path.resolve(),
        expected_sha256=runner_pre.sha256,
        run_git=deps.run_git,
    )
    _require(chart_post == chart_pre, "Chart changed during build")
    _require(stats_post == stats_pre, "Stats.txt changed during build")
    _require(config_post == config_pre, "config.ini changed during build")
    _require(runner_post == runner_pre, "Corpus runner changed during build")

    for hashed in cache_report.pop("_hashed"):
        _assert_hashed_file_unchanged(hashed)
    _assert_hashed_file_unchanged(profile_report.pop("_hashed"))
    expected_cache_entries = {Path(item["path"]) for item in cache_report["files"]}
    _require(
        set(context.paths.fg_response_cache_dir.iterdir()) == expected_cache_entries,
        "Isolated FG cache changed before report publication",
    )
    _require(not context.paths.database_path.exists(), "Direct FG build created the isolated database late")
    _require_empty_directory(context.paths.timeline_cache_dir, label="isolated timeline cache before publication")
    _require_empty_directory(context.paths.optimizer_bin_dir, label="isolated optimizer bin before publication")
    process_post_verification = _memory_info(process)
    virtual_after = runtime.psutil.virtual_memory()
    swap_after = runtime.psutil.swap_memory()
    final_capacity = _validate_capacity_schema_only(deps.read_capacity())

    report = {
        "schema_version": 1,
        "ok": True,
        "completed_build_anchor": True,
        "target": {"before": _git_report(target_pre), "after": _git_report(target_post)},
        "preflight_tool": {
            "before": _git_report(tool_pre),
            "after": _git_report(tool_post),
            "runner": _snapshot_report(runner_pre),
        },
        "inputs": {
            "chart": _snapshot_report(chart_pre),
            "stats": _snapshot_report(stats_pre),
            "config": _snapshot_report(config_pre),
            "chart_parse": chart_report,
            "reference_grid": refs,
        },
        "configuration": {
            "builder_cfg_dict": {},
            "config_loaded": False,
            "reducer_threads": effective_threads,
            "environment": environment_report,
        },
        "cache": cache_report | {"wall_ms": wall_ms},
        "profile_events": profile_report,
        "memory": {
            "completed_build_anchor": True,
            "required_headroom_bytes": _REQUIRED_HEADROOM_BYTES,
            "capacity_before_imports": pre_capacity,
            "capacity_at_build_entry": capacity_at_build_entry,
            "capacity_after": final_capacity,
            "process_before": process_before,
            "process_at_completed_build_return": process_at_completed_return,
            "process_post_verification": process_post_verification,
            "sampled": sampled_memory,
            "physical_before_bytes": {
                "total": int(virtual_before.total),
                "available": int(virtual_before.available),
            },
            "physical_after_bytes": {
                "total": int(virtual_after.total),
                "available": int(virtual_after.available),
            },
            "pagefile_before_bytes": {
                "total": int(swap_before.total),
                "used": int(swap_before.used),
            },
            "pagefile_after_bytes": {
                "total": int(swap_after.total),
                "used": int(swap_after.used),
            },
        },
        "hardware": hardware
        | {
            "numpy_version": str(runtime.np.__version__),
            "numba_version": str(runtime.numba.__version__),
            "psutil_version": str(runtime.psutil.__version__),
            "process_cpu_affinity": [int(value) for value in process.cpu_affinity()],
        },
        "timestamps": {
            "started_epoch_ns": started_wall_ns,
            "ended_epoch_ns": ended_wall_ns,
            "started_utc": dt.datetime.fromtimestamp(started_wall_ns / 1e9, tz=dt.timezone.utc).isoformat(),
            "ended_utc": dt.datetime.fromtimestamp(ended_wall_ns / 1e9, tz=dt.timezone.utc).isoformat(),
        },
    }
    _atomic_write_json(context.paths.artifacts_dir / _COMPLETED_REPORT_NAME, report)
    return report


def _failure_report(context: _ManifestContext, exc: Exception) -> None:
    payload = {
        "schema_version": 1,
        "ok": False,
        "completed_build_anchor": False,
        "error": {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()},
        "target": {"root": str(context.paths.worktree_root), "manifest_head": context.target_head},
        "preflight_tool": {"root": str(context.paths.preflight_tool_root), "manifest_head": context.tool_head},
        "recorded_utc": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
    }
    _atomic_write_json(context.paths.artifacts_dir / _FAILURE_REPORT_NAME, payload)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", required=True)
    parser.add_argument("--chart-relative", required=True)
    parser.add_argument("--expected-chart-sha256", required=True)
    parser.add_argument("--expected-stats-sha256", required=True)
    parser.add_argument("--expected-config-sha256", required=True)
    parser.add_argument("--expected-note-count", required=True, type=int)
    parser.add_argument("--expected-held-count", required=True, type=int)
    parser.add_argument("--expected-cache-version", required=True)
    return parser


def _live_dependencies() -> _Dependencies:
    return _Dependencies(
        run_git=_run_git,
        read_capacity=_windows_capacity_snapshot,
        read_hardware=_windows_hardware_snapshot,
        load_runtime=_load_live_runtime,
        sampler_factory=_live_sampler_factory,
        validate_bench_root=_validate_live_bench_root,
        runner_path=Path(__file__).resolve(),
        hash_randomization=int(sys.flags.hash_randomization),
    )


def main(argv: Iterable[str] | None = None, *, dependencies: _Dependencies | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    context: _ManifestContext | None = None
    deps = dependencies or _live_dependencies()
    try:
        context = _load_manifest(
            Path(args.preflight),
            validate_bench_root=deps.validate_bench_root,
        )
        _execute(args, context, deps)
    except Exception as exc:
        if context is not None:
            try:
                _failure_report(context, exc)
            except Exception as diagnostic_exc:
                print(
                    f"Issue #116 runner failed and could not publish diagnostics: {diagnostic_exc}",
                    file=sys.stderr,
                )
        traceback.print_exc()
        return 1
    print(str(context.paths.artifacts_dir / _COMPLETED_REPORT_NAME))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
