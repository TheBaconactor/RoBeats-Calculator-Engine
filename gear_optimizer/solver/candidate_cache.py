from __future__ import annotations

import ast
import atexit
import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

import numpy as np

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.constants import GEM_SCALE_FEVER, TOTAL_GEM_BUDGET
from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.utils import timing_envelope_timing_context
from gear_optimizer.solver.force_greats_common import STAT_KEYS
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import (
    fg_response_frontier_bundle_cache_key,
    fg_response_frontier_song_cache_key,
)

_CANDIDATE_CACHE_VERSION = "candidate-cache-v1"
_BASE_NAMESPACE = "base"
_FG_NAMESPACE = "fg"
_DISK_FLUSH_BATCH_ROWS = 512


def _candidate_cache_dir() -> Path:
    override = str(env_get("CANDIDATE_CACHE_DIR", "") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "bin" / "candidate_cache"


def default_candidate_cache_path() -> Path:
    return _candidate_cache_dir() / "candidate_cache.sqlite3"


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _copy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload))


def _key_digest(namespace: str, key: tuple[Any, ...]) -> str:
    raw = f"{namespace}:{repr(key)}".encode("utf-8")
    return hashlib.blake2b(raw, digest_size=16).hexdigest()


def _stats_tuple(stats: dict[str, Any] | tuple[Any, ...] | list[Any] | np.ndarray) -> tuple[int, ...]:
    if isinstance(stats, dict):
        missing = [name for name in STAT_KEYS if name not in stats]
        if missing:
            raise ValueError(f"candidate cache stats tuple missing required keys: {missing}")
        return tuple(int(stats.get(name, 0) or 0) for name in STAT_KEYS)
    arr = np.asarray(stats, dtype=np.int64).reshape(-1)
    if int(arr.shape[0]) < len(STAT_KEYS):
        raise ValueError(f"candidate cache stats tuple needs {len(STAT_KEYS)} values, got {arr.shape[0]}")
    return tuple(int(v) for v in arr[: len(STAT_KEYS)].tolist())


def _stats_dict(stats: dict[str, Any] | tuple[Any, ...] | list[Any] | np.ndarray) -> dict[str, int]:
    values = _stats_tuple(stats)
    return {name: int(values[idx]) for idx, name in enumerate(STAT_KEYS)}


def _ref_arrays_key(ref_arrays: dict[str, Any]) -> tuple[bytes, ...]:
    return tuple(
        bytes(array_sig16(np.asarray(ref_arrays[name], dtype=np.float32).reshape(-1)))
        for name in (
            "Perfect Points",
            "Combo Multiplier",
            "Fever Multiplier",
            "Fever Time",
            "Fever Fill Rate",
        )
    )


def _base_song_key(calc_song: dict[str, Any]) -> tuple[Any, ...]:
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    chart_ts = song_data.get("chart_timestamps", None)
    timestamps = chart_ts if chart_ts is not None else song_data.get("timestamps", ())
    note_types = song_data.get("note_types", ())
    return (
        int(len(timestamps)),
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
        bytes(array_sig16(np.asarray(timestamps, dtype=np.float32).reshape(-1))),
        bytes(array_sig16(np.asarray(note_types, dtype=np.int32).reshape(-1))),
    ) + timing_envelope_timing_context(calc_song)


def base_candidate_cache_key(
    *,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    base_stats: dict[str, Any] | tuple[Any, ...] | list[Any] | np.ndarray,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    flags: dict[str, int],
    total_budget: int = TOTAL_GEM_BUDGET,
    gem_scale_fever: int = GEM_SCALE_FEVER,
) -> tuple[Any, ...]:
    flags_key = tuple(sorted((str(k), int(v)) for k, v in (flags or {}).items()))
    return (
        _CANDIDATE_CACHE_VERSION,
        _BASE_NAMESPACE,
        _base_song_key(calc_song),
        _ref_arrays_key(ref_arrays),
        _stats_tuple(base_stats),
        str(primary_color or ""),
        str(secondary_color or ""),
        str(selected_color or ""),
        flags_key,
        int(total_budget),
        int(gem_scale_fever),
    )


def fg_candidate_cache_key(
    *,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_color: str,
    base_components: tuple[int, ...] | list[int] | np.ndarray,
    total_budget: int = TOTAL_GEM_BUDGET,
) -> tuple[Any, ...]:
    components = tuple(int(v) for v in base_components)
    if len(components) != 7:
        raise ValueError(f"FG candidate cache key requires 7 base components, got {len(components)}")
    return (
        _CANDIDATE_CACHE_VERSION,
        _FG_NAMESPACE,
        fg_response_frontier_song_cache_key(calc_song),
        fg_response_frontier_bundle_cache_key(calc_song, ref_arrays),
        _ref_arrays_key(ref_arrays),
        str(selected_color or ""),
        components,
        int(total_budget),
    )


def base_payload_from_result(
    *,
    result: dict[str, Any],
    selected_color: str,
) -> dict[str, Any]:
    payload = {
        "Score": int(result.get("Score", result.get("BaseScore", 0)) or 0),
        "FT": int(result.get("FT", 0) or 0),
        "FF": int(result.get("FF", 0) or 0),
        "GemCounts": dict(result.get("GemCounts") or result.get("gem_counts") or {}),
        "Stats": _stats_dict(result.get("Stats") or {}),
        "Selected Element": str(result.get("Selected Element", selected_color) or selected_color or ""),
    }
    payload["config"] = {
        "FT Gems": int(payload["FT"]),
        "FF Gems": int(payload["FF"]),
        "PP Gems": int(payload["GemCounts"].get("Perfect Points", 0) or 0),
        "CM Gems": int(payload["GemCounts"].get("Combo Multiplier", 0) or 0),
        "FM Gems": int(payload["GemCounts"].get("Fever Multiplier", 0) or 0),
        "Overflow Gems": int(payload["GemCounts"].get("Overflow", 0) or 0),
    }
    payload["FT_gems"] = int(payload["FT"])
    payload["FF_gems"] = int(payload["FF"])
    payload["gem_counts"] = dict(payload["GemCounts"])
    return _validate_base_payload(payload)


def base_payload_from_result_tuple(
    *,
    result: tuple[Any, ...] | list[Any] | np.ndarray,
    base_stats: dict[str, Any] | tuple[Any, ...] | list[Any] | np.ndarray,
    selected_color: str,
) -> dict[str, Any]:
    row = tuple(int(v) for v in np.asarray(result, dtype=np.int64).reshape(-1)[:7].tolist())
    if len(row) != 7:
        raise ValueError(f"base candidate cache result tuple needs 7 values, got {len(row)}")
    score, ft, ff, g_pp, g_cm, g_fm, g_ov = row
    gem_counts = {
        "Perfect Points": int(g_pp),
        "Combo Multiplier": int(g_cm),
        "Fever Multiplier": int(g_fm),
        "Overflow": int(g_ov),
    }
    stats = apply_gems_to_base_stats(
        _stats_dict(base_stats),
        str(selected_color or ""),
        int(ft),
        int(ff),
        int(g_pp),
        int(g_cm),
        int(g_fm),
        int(g_ov),
        add_missing_element_key=False,
    )
    return base_payload_from_result(
        result={
            "Score": int(score),
            "FT": int(ft),
            "FF": int(ff),
            "GemCounts": gem_counts,
            "Stats": stats,
            "Selected Element": str(selected_color or ""),
        },
        selected_color=str(selected_color or ""),
    )


def fg_payload_from_materialized(
    *,
    raw_best_score: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    force = dict(payload.get("ForceGreats") or {})
    cached = {
        "raw_best_score": int(raw_best_score),
        "exact_score": int(payload.get("Score", 0) or 0),
        "FT": int(payload.get("FT", 0) or 0),
        "FF": int(payload.get("FF", 0) or 0),
        "GemCounts": dict(payload.get("GemCounts") or {}),
        "forced_counts": [int(v) for v in payload.get("forced_counts", [])],
        "response_surface": [int(v) for v in payload.get("response_surface", [])],
        "ForceGreats": force,
    }
    return _validate_fg_payload(cached)


def materialize_fg_payload_from_cache(
    *,
    cached: dict[str, Any],
    eval_data: dict[str, Any],
    base_stats: dict[str, Any],
    paired_base_score: int,
    selected_element: str,
) -> dict[str, Any]:
    cached = _validate_fg_payload(cached)
    gem_counts = dict(cached["GemCounts"])
    ft = int(cached["FT"])
    ff = int(cached["FF"])
    final_stats = apply_gems_to_base_stats(
        dict(base_stats),
        str(selected_element or ""),
        ft,
        ff,
        int(gem_counts.get("Perfect Points", 0) or 0),
        int(gem_counts.get("Combo Multiplier", 0) or 0),
        int(gem_counts.get("Fever Multiplier", 0) or 0),
        int(gem_counts.get("Overflow", 0) or 0),
    )
    force = dict(cached["ForceGreats"])
    force["final_score"] = int(cached["exact_score"])
    payload = dict(eval_data)
    payload["BaseStats"] = dict(base_stats)
    payload["Stats"] = dict(final_stats)
    payload["BaseScore"] = int(paired_base_score)
    payload["Score"] = int(cached["exact_score"])
    payload["Selected Element"] = str(selected_element or payload.get("Selected Element", "") or "")
    payload["GemCounts"] = gem_counts
    payload["FT"] = ft
    payload["FF"] = ff
    payload["forced_counts"] = list(cached["forced_counts"])
    payload["response_surface"] = list(cached["response_surface"])
    payload["ForceGreats"] = force
    return payload


def _validate_base_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("base candidate cache payload must be a dict")
    for field in ("Score", "FT", "FF"):
        if int(payload.get(field, -1)) < 0:
            raise ValueError(f"base candidate cache payload has invalid {field}")
    if not isinstance(payload.get("GemCounts"), dict):
        raise ValueError("base candidate cache payload requires GemCounts")
    _stats_tuple(payload.get("Stats") or {})
    if not str(payload.get("Selected Element", "") or ""):
        raise ValueError("base candidate cache payload requires Selected Element")
    out = _copy_payload(payload)
    out["Score"] = int(out["Score"])
    out["FT"] = int(out["FT"])
    out["FF"] = int(out["FF"])
    out["Stats"] = _stats_dict(out["Stats"])
    out["GemCounts"] = {str(k): int(v) for k, v in out["GemCounts"].items()}
    out["gem_counts"] = dict(out["GemCounts"])
    out["FT_gems"] = int(out["FT"])
    out["FF_gems"] = int(out["FF"])
    return out


def _validate_fg_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("FG candidate cache payload must be a dict")
    for field in ("raw_best_score", "exact_score", "FT", "FF"):
        if int(payload.get(field, -1)) < 0:
            raise ValueError(f"FG candidate cache payload has invalid {field}")
    gem_counts = payload.get("GemCounts")
    if not isinstance(gem_counts, dict):
        raise ValueError("FG candidate cache payload requires GemCounts")
    force = payload.get("ForceGreats")
    if not isinstance(force, dict):
        raise ValueError("FG candidate cache payload requires ForceGreats")
    surface = payload.get("response_surface")
    if not isinstance(surface, list) or len(surface) != 11:
        raise ValueError("FG candidate cache payload requires an 11-int response_surface")
    forced_counts = payload.get("forced_counts")
    if not isinstance(forced_counts, list):
        raise ValueError("FG candidate cache payload requires forced_counts")
    out = _copy_payload(payload)
    out["raw_best_score"] = int(out["raw_best_score"])
    out["exact_score"] = int(out["exact_score"])
    out["FT"] = int(out["FT"])
    out["FF"] = int(out["FF"])
    out["GemCounts"] = {str(k): int(v) for k, v in out["GemCounts"].items()}
    out["response_surface"] = [int(v) for v in out["response_surface"]]
    out["forced_counts"] = [int(v) for v in out["forced_counts"]]
    return out


class CandidateCache:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else default_candidate_cache_path()
        self._lock = threading.RLock()
        self._base: dict[tuple[Any, ...], dict[str, Any]] = {}
        self._fg: dict[tuple[Any, ...], dict[str, Any]] = {}
        self._pending_disk_rows: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.base_hits = 0
        self.base_misses = 0
        self.base_admits = 0
        self.fg_hits = 0
        self.fg_misses = 0
        self.fg_admits = 0
        self._load_disk()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(self.db_path))
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS candidate_cache (
                namespace TEXT NOT NULL,
                key_digest TEXT NOT NULL,
                key_repr TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY(namespace, key_digest)
            )
            """
        )
        return con

    def _load_disk(self) -> None:
        if not self.db_path.exists():
            return
        with self._connect() as con:
            rows = con.execute("SELECT namespace, key_repr, payload_json FROM candidate_cache").fetchall()
        with self._lock:
            for namespace, key_repr, payload_json in rows:
                key = ast.literal_eval(str(key_repr))
                if not isinstance(key, tuple):
                    raise ValueError("candidate cache disk key is not a tuple")
                payload = json.loads(str(payload_json))
                if namespace == _BASE_NAMESPACE:
                    self._base[key] = _validate_base_payload(payload)
                elif namespace == _FG_NAMESPACE:
                    self._fg[key] = _validate_fg_payload(payload)
                else:
                    raise ValueError(f"candidate cache disk row has unknown namespace {namespace!r}")

    def _flush_rows(self, rows: list[tuple[str, tuple[Any, ...], dict[str, Any]]]) -> None:
        if not rows:
            return
        with self._connect() as con:
            con.executemany(
                """
                INSERT OR REPLACE INTO candidate_cache(namespace, key_digest, key_repr, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (namespace, _key_digest(namespace, key), repr(key), _json_dumps(payload))
                    for namespace, key, payload in rows
                ],
            )

    def flush(self) -> None:
        with self._lock:
            rows = list(self._pending_disk_rows)
            self._pending_disk_rows.clear()
        self._flush_rows(rows)

    def _queue_disk_row(self, namespace: str, key: tuple[Any, ...], payload: dict[str, Any]) -> None:
        rows: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        with self._lock:
            self._pending_disk_rows.append((namespace, key, _copy_payload(payload)))
            if len(self._pending_disk_rows) >= _DISK_FLUSH_BATCH_ROWS:
                rows = list(self._pending_disk_rows)
                self._pending_disk_rows.clear()
        self._flush_rows(rows)

    def get_base(self, key: tuple[Any, ...]) -> dict[str, Any] | None:
        with self._lock:
            payload = self._base.get(key)
            if payload is None:
                self.base_misses += 1
                return None
            self.base_hits += 1
            return _validate_base_payload(payload)

    def put_base(self, key: tuple[Any, ...], payload: dict[str, Any]) -> None:
        payload = _validate_base_payload(payload)
        with self._lock:
            self._base[key] = payload
            self.base_admits += 1
        self._queue_disk_row(_BASE_NAMESPACE, key, payload)

    def get_fg(self, key: tuple[Any, ...]) -> dict[str, Any] | None:
        with self._lock:
            payload = self._fg.get(key)
            if payload is None:
                self.fg_misses += 1
                return None
            self.fg_hits += 1
            return _validate_fg_payload(payload)

    def put_fg(self, key: tuple[Any, ...], payload: dict[str, Any]) -> None:
        payload = _validate_fg_payload(payload)
        with self._lock:
            self._fg[key] = payload
            self.fg_admits += 1
        self._queue_disk_row(_FG_NAMESPACE, key, payload)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "base_entries": int(len(self._base)),
                "base_hits": int(self.base_hits),
                "base_misses": int(self.base_misses),
                "base_admits": int(self.base_admits),
                "pending_disk_rows": int(len(self._pending_disk_rows)),
                "fg_entries": int(len(self._fg)),
                "fg_hits": int(self.fg_hits),
                "fg_misses": int(self.fg_misses),
                "fg_admits": int(self.fg_admits),
            }


_GLOBAL_CACHE: CandidateCache | None = None
_GLOBAL_LOCK = threading.RLock()


def get_candidate_cache() -> CandidateCache:
    global _GLOBAL_CACHE
    with _GLOBAL_LOCK:
        if _GLOBAL_CACHE is None:
            _GLOBAL_CACHE = CandidateCache()
        return _GLOBAL_CACHE


def reset_candidate_cache_for_tests(db_path: Path | str | None = None) -> CandidateCache:
    global _GLOBAL_CACHE
    with _GLOBAL_LOCK:
        if _GLOBAL_CACHE is not None:
            _GLOBAL_CACHE.flush()
        _GLOBAL_CACHE = CandidateCache(db_path)
        return _GLOBAL_CACHE


@atexit.register
def _close_candidate_cache() -> None:
    with _GLOBAL_LOCK:
        cache = _GLOBAL_CACHE
    if cache is not None:
        cache.flush()
