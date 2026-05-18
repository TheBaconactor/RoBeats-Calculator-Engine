from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import psutil


def utc_ts() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y%m%d_%H%M%S")


def truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_artifact_paths(path_or_paths: Path | list[Path] | tuple[Path, ...] | None) -> list[Path]:
    if path_or_paths is None:
        return []

    raw_paths: list[Path]
    if isinstance(path_or_paths, Path):
        raw_paths = [path_or_paths]
    elif isinstance(path_or_paths, (list, tuple)):
        raw_paths = [Path(p) for p in path_or_paths if p is not None]
    else:
        raw_paths = [Path(path_or_paths)]

    out: list[Path] = []
    seen: set[str] = set()

    def _add(path: Path) -> None:
        try:
            key = str(path.resolve())
        except Exception:
            key = str(path)
        if key in seen:
            return
        seen.add(key)
        out.append(path)

    for base_path in raw_paths:
        if base_path.exists():
            _add(base_path)
        try:
            parent = base_path.parent
            stem = str(base_path.stem or "")
            suffix = str(base_path.suffix or "")
            pattern = f"{stem}.w*{suffix}" if suffix else f"{stem}.w*"
            for candidate in sorted(parent.glob(pattern)):
                if candidate.is_file():
                    _add(candidate)
        except Exception:
            continue

    return out


def normalize_pid_list(*, target_pid: int | None = None, target_pids: Iterable[int] | None = None) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    raw_values = list(target_pids or [])
    if target_pid is not None:
        raw_values.append(target_pid)
    for raw in raw_values:
        try:
            pid = int(raw)
        except Exception:
            continue
        if pid <= 0 or pid in seen:
            continue
        seen.add(pid)
        out.append(pid)
    return out


def resolve_live_target_pids(
    *,
    target_pid: int | None = None,
    target_pids_fn: Callable[[], Iterable[int]] | None = None,
) -> list[int]:
    dynamic_pids: list[int] = []
    if target_pids_fn is not None:
        try:
            dynamic_pids = list(target_pids_fn() or [])
        except Exception:
            dynamic_pids = []
    return normalize_pid_list(target_pid=target_pid, target_pids=dynamic_pids)


def get_process_tree_pids(root_pid: int) -> list[int]:
    root_pid = int(root_pid)
    try:
        root = psutil.Process(root_pid)
    except Exception:
        return normalize_pid_list(target_pid=root_pid)

    pids = [root_pid]
    try:
        children = root.children(recursive=True)
    except Exception:
        children = []
    for child in children:
        try:
            pids.append(int(child.pid))
        except Exception:
            continue
    return normalize_pid_list(target_pids=pids)


@dataclass(frozen=True)
class RunPaths:
    out_dir: Path
    stdout_log: Path
    cpu_jsonl: Path
    typeperf_csv: Path
    getcounter_csv: Path
    stage_profile_json: Path
    profile_events_jsonl: Path
    summary_json: Path


def default_out_dir() -> Path:
    return Path("artifacts") / "profile" / f"run_{utc_ts()}"
