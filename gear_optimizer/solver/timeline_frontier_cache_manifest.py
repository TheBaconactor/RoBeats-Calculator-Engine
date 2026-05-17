from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import logging

import numpy as np

from gear_optimizer.core.array_signature import array_sig16



logger = logging.getLogger(__name__)
_MANIFEST_SCHEMA = 1
_MANIFEST_FILE_NAME = "manifest_v1.json"
_TIMING_ENVELOPE_MODE = "perfect_window"
_MANIFEST_LOCK = threading.RLock()


@dataclass(frozen=True)
class TimelineFrontierCacheManifestPlan:
    total_paths: int
    hit_paths: tuple[str, ...]
    missing_paths: tuple[str, ...]
    key_by_norm_path: dict[str, str]

    @property
    def hit_count(self) -> int:
        return int(len(self.hit_paths))


def _frontier_cache_dir() -> Path:
    from gear_optimizer.solver.taichi_gem.api.timeline import _frontier_disk_cache_dir

    return _frontier_disk_cache_dir()


def _frontier_cache_version() -> str:
    from gear_optimizer.solver.taichi_gem.api.timeline import _FRONTIER_DISK_CACHE_VERSION

    return str(_FRONTIER_DISK_CACHE_VERSION)


def manifest_path(cache_dir: str | os.PathLike[str] | None = None) -> Path:
    root = Path(cache_dir) if cache_dir is not None else _frontier_cache_dir()
    return root / _MANIFEST_FILE_NAME


def _normalize_path(path_text: str) -> str:
    return os.path.abspath(str(path_text or "")).casefold()


def _song_identity(path_text: str) -> tuple[str, int, int] | None:
    try:
        abs_path = os.path.abspath(str(path_text))
        st = os.stat(abs_path)
    except Exception as e:
        logger.debug(f"timeline_frontier_cache_manifest:_song_identity: {e}")
        return None
    mtime_ns_raw = getattr(st, "st_mtime_ns", None)
    if isinstance(mtime_ns_raw, int):
        mtime_ns = int(mtime_ns_raw)
    else:
        mtime_ns = int(float(st.st_mtime) * 1e9)
    return abs_path, int(mtime_ns), int(st.st_size)


def _ref_axes_signature(ref_arrays: dict) -> str:
    ref_ft = np.asarray((ref_arrays or {}).get("Fever Time", ()), dtype=np.float32).reshape(-1)
    ref_ff = np.asarray((ref_arrays or {}).get("Fever Fill Rate", ()), dtype=np.float32).reshape(-1)
    return bytes(array_sig16(ref_ft) + array_sig16(ref_ff)).hex()


def _manifest_key(
    *,
    abs_song_path: str,
    mtime_ns: int,
    file_size: int,
    ref_sig_hex: str,
    frontier_version: str,
) -> str:
    raw = "|".join(
        (
            str(frontier_version),
            _TIMING_ENVELOPE_MODE,
            str(ref_sig_hex),
            str(abs_song_path).casefold(),
            str(mtime_ns),
            str(file_size),
        )
    )
    return hashlib.blake2b(raw.encode("utf-8"), digest_size=16).hexdigest()


def _load_manifest(path: Path, *, frontier_version: str) -> dict[str, dict]:
    with _MANIFEST_LOCK:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.debug(f"timeline_frontier_cache_manifest:_load_manifest: {e}")
            return {}
        if not isinstance(payload, dict):
            return {}
        try:
            schema = int(payload.get("schema", 0) or 0)
        except Exception as e:
            logger.debug(f"timeline_frontier_cache_manifest:_load_manifest: {e}")
            schema = 0
        if schema != int(_MANIFEST_SCHEMA):
            return {}
        if str(payload.get("frontier_version", "") or "") != str(frontier_version):
            return {}
        entries = payload.get("entries", {})
        if not isinstance(entries, dict):
            return {}
        out: dict[str, dict] = {}
        for k, v in entries.items():
            if isinstance(k, str) and isinstance(v, dict):
                out[str(k)] = dict(v)
        return out


def _save_manifest(path: Path, *, frontier_version: str, entries: dict[str, dict]) -> None:
    payload = {
        "schema": int(_MANIFEST_SCHEMA),
        "frontier_version": str(frontier_version),
        "entries": entries,
    }
    tmp = path.with_name(f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp")
    with _MANIFEST_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=True), encoding="utf-8")
        tmp.replace(path)


def build_manifest_plan(song_paths: Iterable[str], ref_arrays: dict) -> TimelineFrontierCacheManifestPlan:
    paths = [str(p) for p in list(song_paths or []) if str(p or "").strip()]
    total_paths = int(len(paths))
    if total_paths <= 0:
        return TimelineFrontierCacheManifestPlan(
            total_paths=0,
            hit_paths=(),
            missing_paths=(),
            key_by_norm_path={},
        )

    frontier_version = _frontier_cache_version()
    path = manifest_path()
    entries = _load_manifest(path, frontier_version=frontier_version)
    ref_sig_hex = _ref_axes_signature(ref_arrays)

    hits: list[str] = []
    misses: list[str] = []
    key_by_norm: dict[str, str] = {}
    for song_path in paths:
        identity = _song_identity(song_path)
        if identity is None:
            misses.append(song_path)
            continue
        abs_path, mtime_ns, file_size = identity
        key = _manifest_key(
            abs_song_path=abs_path,
            mtime_ns=int(mtime_ns),
            file_size=int(file_size),
            ref_sig_hex=ref_sig_hex,
            frontier_version=frontier_version,
        )
        norm_path = _normalize_path(abs_path)
        key_by_norm[norm_path] = key
        entry = entries.get(key)
        cache_file = str((entry or {}).get("cache_file", "") or "").strip()
        if cache_file and os.path.exists(cache_file):
            hits.append(song_path)
            continue
        misses.append(song_path)

    return TimelineFrontierCacheManifestPlan(
        total_paths=int(total_paths),
        hit_paths=tuple(hits),
        missing_paths=tuple(misses),
        key_by_norm_path=key_by_norm,
    )


def apply_manifest_results(
    *,
    plan: TimelineFrontierCacheManifestPlan,
    results: Iterable[object],
) -> int:
    frontier_version = _frontier_cache_version()
    path = manifest_path()
    entries = _load_manifest(path, frontier_version=frontier_version)
    updated = 0
    now_ns = int(time.time_ns())

    for item in list(results or []):
        if item is None:
            continue
        song_path = str(getattr(item, "path", "") or "").strip()
        cache_file = str(getattr(item, "cache_file", "") or "").strip()
        source = str(getattr(item, "source", "") or "").strip().lower()
        if source not in {"built", "disk", "memory"}:
            continue
        if not song_path or not cache_file or not os.path.exists(cache_file):
            continue
        key = plan.key_by_norm_path.get(_normalize_path(song_path))
        if not key:
            continue
        entries[key] = {
            "cache_file": str(cache_file),
            "updated_at_ns": int(now_ns),
        }
        updated += 1

    if updated <= 0:
        return 0
    _save_manifest(path, frontier_version=frontier_version, entries=entries)
    return int(updated)


__all__ = [
    "TimelineFrontierCacheManifestPlan",
    "apply_manifest_results",
    "build_manifest_plan",
    "manifest_path",
]
