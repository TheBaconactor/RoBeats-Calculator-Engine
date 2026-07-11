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
    derived_cache_file_fn: Callable[[str], str | None] | None = None,
    drift_sample_size: int = 8,
    persist_validated_entries: bool = True,
) -> FrontierCacheManifestPlan:
    paths = [str(path) for path in list(song_paths or []) if str(path or "").strip()]
    if not paths:
        return FrontierCacheManifestPlan(0, (), (), {})

    entries = _load_manifest(manifest_path, cache_version=cache_version, version_field=version_field)
    hits: list[str] = []
    misses: list[str] = []
    key_by_norm: dict[str, str] = {}
    recorded_file_by_norm: dict[str, str] = {}
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
            # Identity fast-path compares cache-file SIZE only, never mtime. External copies and
            # filesystem maintenance can mutate mtime with no content change. Comparing mtime here
            # defeats the fast-path: the recorded mtime becomes stale, forcing a full per-file
            # re-validation on every startup (measured: FG fast-path hit 0/6704 -> ~100s warm verify).
            # The cache path is content-addressed (digest of the cache key) and builds are deterministic,
            # so a same-size file at the same path is the same validated bundle; corruption is still
            # caught loudly by the loader on the real read path.
            _cache_abs_path, _cache_mtime_ns, cache_size = cache_identity
            entry_size = entry.get("cache_size")
            if entry_size is None:
                cache_hit = False
            else:
                try:
                    cache_hit = int(entry_size) == int(cache_size)
                except (TypeError, ValueError):
                    cache_hit = False
        if cache_identity is None and derived_cache_file_fn is not None and cache_file_validator is not None:
            try:
                derived_cache_file = str(derived_cache_file_fn(song_path) or "").strip()
            except Exception as exc:
                logger.debug("frontier_cache_manifest:derived_cache_file_fn: %s", exc)
                derived_cache_file = ""
            derived_identity = _path_identity(derived_cache_file) if derived_cache_file else None
            if derived_identity is not None:
                cache_file = derived_cache_file
                cache_identity = derived_identity

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
            recorded_file_by_norm[normalize_manifest_path(abs_path)] = cache_file
        else:
            misses.append(song_path)

    if persist_validated_entries and updated_entries > 0:
        _save_manifest(manifest_path, cache_version=cache_version, version_field=version_field, entries=entries)

    if _detect_cache_key_drift(
        hits,
        recorded_file_by_norm=recorded_file_by_norm,
        derived_cache_file_fn=derived_cache_file_fn,
        drift_sample_size=drift_sample_size,
    ):
        # The manifest's identity inputs (cache version, chart mtime/size, ref/stat sigs) did not
        # move, yet the content-addressed cache key the runtime derives points at a DIFFERENT file
        # than the one this manifest validated. That means the key-derivation code changed without
        # a cache-version bump (the 2026-07-02 incident: PR #89 changed great_candidates, the
        # fast-path kept reporting stale bundles as ready, and every affected song failed prep).
        # Drop the fast-path for this run: the per-file verify derives true keys and rebuilds.
        return FrontierCacheManifestPlan(
            total_paths=len(paths),
            hit_paths=(),
            missing_paths=tuple(paths),
            key_by_norm_path=key_by_norm,
        )

    return FrontierCacheManifestPlan(
        total_paths=len(paths),
        hit_paths=tuple(hits),
        missing_paths=tuple(misses),
        key_by_norm_path=key_by_norm,
    )


def _detect_cache_key_drift(
    hit_paths: list[str],
    *,
    recorded_file_by_norm: dict[str, str],
    derived_cache_file_fn: Callable[[str], str | None] | None,
    drift_sample_size: int,
) -> bool:
    """Sample manifest hits and verify the recorded cache file is the one the CURRENT key derives.

    The fast-path identity (cache version + chart mtime/size + ref/stat sigs) cannot see changes to
    the key-derivation code itself: if key inputs change without a version bump, every recorded
    entry silently points at a file the runtime will never ask for. Deriving the true key for a
    handful of hits costs a few chart parses (~50ms each) and turns that silent skip into a loud
    full re-verify. Derivation errors are skipped (unreadable charts are the per-file path's
    problem, not a drift signal)."""
    if derived_cache_file_fn is None or not hit_paths:
        return False
    sample_count = max(1, min(int(drift_sample_size), len(hit_paths)))
    step = max(1, len(hit_paths) // sample_count)
    for song_path in hit_paths[::step][:sample_count]:
        recorded = recorded_file_by_norm.get(normalize_manifest_path(song_path), "")
        if not recorded:
            continue
        try:
            derived = derived_cache_file_fn(song_path)
        except Exception as exc:
            logger.debug("frontier_cache_manifest:derived_cache_file_fn: %s", exc)
            continue
        if not derived:
            continue
        if normalize_manifest_path(str(derived)) != normalize_manifest_path(recorded):
            logger.warning(
                "[FrontierCacheManifest] Cache-key drift detected: %s derives %s but the manifest "
                "recorded %s. Key-derivation inputs changed without a cache-version bump; dropping "
                "the manifest fast-path for this run (full per-file verify + rebuild).",
                song_path,
                derived,
                recorded,
            )
            return True
    return False


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
