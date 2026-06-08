from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

logger = logging.getLogger(__name__)
_SCHEMA = 1
_TIMING_ENVELOPE_MODE = "perfect_window"
_LOCK = threading.RLock()


@dataclass(frozen=True)
class FrontierCacheManifestPlan:
    total_paths: int
    hit_paths: tuple[str, ...]
    missing_paths: tuple[str, ...]
    key_by_norm_path: dict[str, str]

    @property
    def hit_count(self) -> int:
        return int(len(self.hit_paths))


def normalize_manifest_path(path_text: str) -> str:
    return os.path.abspath(str(path_text or "")).casefold()


def _path_identity(path_text: str) -> tuple[str, int, int] | None:
    try:
        abs_path = os.path.abspath(str(path_text))
        st = os.stat(abs_path)
    except OSError as exc:
        logger.debug("frontier_cache_manifest:_path_identity: %s", exc)
        return None
    mtime_ns_raw = getattr(st, "st_mtime_ns", None)
    mtime_ns = int(mtime_ns_raw) if isinstance(mtime_ns_raw, int) else int(float(st.st_mtime) * 1e9)
    return abs_path, int(mtime_ns), int(st.st_size)


def _manifest_key(
    *,
    cache_version: str,
    ref_sig_hex: str,
    stat_sig_hex: str | None,
    abs_song_path: str,
    mtime_ns: int,
    file_size: int,
) -> str:
    parts = [
        str(cache_version),
        _TIMING_ENVELOPE_MODE,
        str(ref_sig_hex),
    ]
    if stat_sig_hex is not None:
        parts.append(str(stat_sig_hex))
    parts.extend(
        (
            str(abs_song_path).casefold(),
            str(mtime_ns),
            str(file_size),
        )
    )
    return hashlib.blake2b("|".join(parts).encode("utf-8"), digest_size=16).hexdigest()


def _load_manifest(path: Path, *, cache_version: str, version_field: str) -> dict[str, dict]:
    with _LOCK:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("frontier_cache_manifest:_load_manifest: %s", exc)
            return {}
        if not isinstance(payload, dict):
            return {}
        try:
            schema = int(payload.get("schema", 0) or 0)
        except (TypeError, ValueError) as exc:
            logger.debug("frontier_cache_manifest:_load_manifest_schema: %s", exc)
            return {}
        if schema != _SCHEMA or str(payload.get(version_field, "") or "") != str(cache_version):
            return {}
        entries = payload.get("entries", {})
        if not isinstance(entries, dict):
            return {}
        return {str(k): dict(v) for k, v in entries.items() if isinstance(k, str) and isinstance(v, dict)}


def _save_manifest(path: Path, *, cache_version: str, version_field: str, entries: dict[str, dict]) -> None:
    payload = {
        "schema": _SCHEMA,
        version_field: str(cache_version),
        "entries": entries,
    }
    tmp = path.with_name(f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp")
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=True), encoding="utf-8")
        tmp.replace(path)


def build_manifest_plan(
    song_paths: Iterable[str],
    *,
    manifest_path: Path,
    cache_version: str,
    version_field: str,
    ref_sig_hex: str,
    stat_sig_hex: str | None = None,
    cache_file_validator: Callable[[str], bool] | None = None,
) -> FrontierCacheManifestPlan:
    paths = [str(path) for path in list(song_paths or []) if str(path or "").strip()]
    if not paths:
        return FrontierCacheManifestPlan(0, (), (), {})

    entries = _load_manifest(manifest_path, cache_version=cache_version, version_field=version_field)
    hits: list[str] = []
    misses: list[str] = []
    key_by_norm: dict[str, str] = {}
    updated_entries = 0
    for song_path in paths:
        identity = _path_identity(song_path)
        if identity is None:
            misses.append(song_path)
            continue
        abs_path, mtime_ns, file_size = identity
        key = _manifest_key(
            cache_version=cache_version,
            ref_sig_hex=ref_sig_hex,
            stat_sig_hex=stat_sig_hex,
            abs_song_path=abs_path,
            mtime_ns=mtime_ns,
            file_size=file_size,
        )
        key_by_norm[normalize_manifest_path(abs_path)] = key
        entry = entries.get(key) or {}
        cache_file = str(entry.get("cache_file", "") or "").strip()
        cache_identity = _path_identity(cache_file) if cache_file else None
        cache_hit = cache_identity is not None
        if cache_hit:
            _cache_abs_path, cache_mtime_ns, cache_size = cache_identity
            entry_mtime_ns = entry.get("cache_mtime_ns")
            entry_size = entry.get("cache_size")
            if entry_mtime_ns is None or entry_size is None:
                cache_hit = False
            else:
                try:
                    cache_hit = int(entry_mtime_ns) == int(cache_mtime_ns) and int(entry_size) == int(cache_size)
                except (TypeError, ValueError):
                    cache_hit = False
        if cache_identity is not None and not cache_hit and cache_file_validator is not None:
            try:
                cache_hit = bool(cache_file_validator(cache_file))
            except Exception as exc:
                logger.debug("frontier_cache_manifest:cache_file_validator: %s", exc)
                cache_hit = False
            if cache_hit:
                cache_abs_path, cache_mtime_ns, cache_size = cache_identity
                entries[key] = {
                    "cache_file": str(cache_abs_path),
                    "cache_mtime_ns": int(cache_mtime_ns),
                    "cache_size": int(cache_size),
                    "updated_at_ns": int(time.time_ns()),
                }
                updated_entries += 1
        if cache_hit:
            hits.append(song_path)
        else:
            misses.append(song_path)

    if updated_entries > 0:
        _save_manifest(manifest_path, cache_version=cache_version, version_field=version_field, entries=entries)

    return FrontierCacheManifestPlan(
        total_paths=len(paths),
        hit_paths=tuple(hits),
        missing_paths=tuple(misses),
        key_by_norm_path=key_by_norm,
    )


def apply_manifest_results(
    *,
    plan: FrontierCacheManifestPlan,
    manifest_path: Path,
    cache_version: str,
    version_field: str,
    results: Iterable[object],
    cache_file_validator: Callable[[str], bool] | None = None,
) -> int:
    entries = _load_manifest(manifest_path, cache_version=cache_version, version_field=version_field)
    updated = 0
    now_ns = int(time.time_ns())
    for item in list(results or []):
        song_path = str(getattr(item, "path", "") or "").strip()
        cache_file = str(getattr(item, "cache_file", "") or "").strip()
        source = str(getattr(item, "source", "") or "").strip().lower()
        if source not in {"built", "disk", "memory"} or not song_path or not cache_file:
            continue
        cache_identity = _path_identity(cache_file)
        if cache_identity is None:
            continue
        if cache_file_validator is not None:
            try:
                if not bool(cache_file_validator(cache_file)):
                    continue
            except Exception as exc:
                logger.debug("frontier_cache_manifest:apply_cache_file_validator: %s", exc)
                continue
        cache_abs_path, cache_mtime_ns, cache_size = cache_identity
        if not os.path.exists(cache_abs_path):
            continue
        key = plan.key_by_norm_path.get(normalize_manifest_path(song_path))
        if not key:
            continue
        entries[key] = {
            "cache_file": str(cache_abs_path),
            "cache_mtime_ns": int(cache_mtime_ns),
            "cache_size": int(cache_size),
            "updated_at_ns": now_ns,
        }
        updated += 1

    if updated > 0:
        _save_manifest(manifest_path, cache_version=cache_version, version_field=version_field, entries=entries)
    return int(updated)
