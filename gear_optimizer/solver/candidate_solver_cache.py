from __future__ import annotations

import hashlib
import struct
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.constants import PATHS
from gear_optimizer.core.utils import safe_int, timing_envelope_timing_context
from gear_optimizer.solver.scoring.stats_scoring import _force_greats_counts_to_dict


FG_CACHE_SCHEMA_VERSION = 1
FG_CACHE_SECTION_CAP = 20
BASE_CACHE_SCHEMA_VERSION = 5
_FG_ROW = struct.Struct("<Q7hiiiiBBBBBBBI20h20h")
_BASE_ROW = struct.Struct("<Q7h8i")
_PATH_LOCKS: dict[Path, threading.Lock] = {}
_PATH_LOCKS_GUARD = threading.Lock()


def _song_timing_cache_key(calc_song: dict) -> tuple:
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    cached = calc_song.get("_gpu_timing_cache_key_frontier", None)
    if isinstance(cached, tuple) and len(cached) == 11:
        return cached
    chart_ts = song_data.get("chart_timestamps", None)
    timestamps = chart_ts if chart_ts is not None else song_data.get("timestamps", ())
    ts_sig = song_data.get("_chart_timestamps_sig", None)
    if not isinstance(ts_sig, (bytes, bytearray, memoryview)) or len(ts_sig) != 16:
        ts_sig = array_sig16(timestamps)
    nt_sig = song_data.get("_note_types_sig", None)
    if not isinstance(nt_sig, (bytes, bytearray, memoryview)) or len(nt_sig) != 16:
        nt_sig = array_sig16(song_data.get("note_types"))
    key = (
        str(meta.get("Song Name", "")),
        str(meta.get("Difficulty", "")),
        int(len(timestamps)),
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
        bytes(ts_sig),
        bytes(nt_sig),
    ) + timing_envelope_timing_context(calc_song)
    calc_song["_gpu_timing_cache_key_frontier"] = key
    return key


@dataclass(frozen=True)
class FgCandidateCacheValue:
    final_score: int
    base_score: int
    score_penalty: int
    fill_penalty: int
    ft: int
    ff: int
    gems_pp: int
    gems_cm: int
    gems_fm: int
    gems_ov: int
    num_sections: int
    non_fever_base: int
    config_counts: tuple[int, ...]
    fp_targets: tuple[int, ...]

    def to_result(self) -> dict[str, Any]:
        counts = list(self.config_counts)
        return {
            "base_score": int(self.base_score),
            "final_score": int(self.final_score),
            "score_penalty": int(self.score_penalty),
            "fill_penalty": int(self.fill_penalty),
            "total_penalty": int(self.score_penalty) + int(self.fill_penalty),
            "num_non_fever_sections": int(self.num_sections),
            "penalty_analysis": {},
            "config_counts": counts,
            "config_dict": _force_greats_counts_to_dict(counts, max(2, len(counts))),
            "fp_targets": list(self.fp_targets),
            "non_fever_base": int(self.non_fever_base),
            "gem_counts": {
                "Perfect Points": int(self.gems_pp),
                "Combo Multiplier": int(self.gems_cm),
                "Fever Multiplier": int(self.gems_fm),
                "Element": int(self.gems_ov),
            },
            "FT": int(self.ft),
            "FF": int(self.ff),
        }


@dataclass(frozen=True)
class BaseCandidateCacheValue:
    score: int
    combo_idx: int
    ft: int
    ff: int
    gems_pp: int
    gems_cm: int
    gems_fm: int
    gems_ov: int

    def result8(self) -> tuple[int, ...]:
        return (
            int(self.score),
            int(self.combo_idx),
            int(self.ft),
            int(self.ff),
            int(self.gems_pp),
            int(self.gems_cm),
            int(self.gems_fm),
            int(self.gems_ov),
        )

    def gpu_result6(self) -> tuple[int, ...]:
        return (
            int(self.score),
            int(self.combo_idx),
            int(self.gems_pp),
            int(self.gems_cm),
            int(self.gems_fm),
            int(self.gems_ov),
        )


def solver_candidate_cache_root() -> Path:
    return Path(PATHS.bin_dir) / "solver_candidate_cache"


def fg_cache_path(context_digest: str) -> Path:
    digest = str(context_digest or "").strip()
    if len(digest) != 32:
        raise ValueError(f"invalid FG candidate cache digest: {context_digest!r}")
    return solver_candidate_cache_root() / "fg" / f"{digest}.bin"


def base_cache_path(context_digest: str) -> Path:
    digest = str(context_digest or "").strip()
    if len(digest) != 32:
        raise ValueError(f"invalid base candidate cache digest: {context_digest!r}")
    return solver_candidate_cache_root() / "base" / f"{digest}.bin"


def fg_context_digest(
    *,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    num_sections: int,
    non_fever_base: int,
    search_ranges: tuple[int, int, int, int] | None,
    solver_version: int,
) -> str:
    h = hashlib.blake2b(digest_size=16)
    h.update(f"fg-cache-v{FG_CACHE_SCHEMA_VERSION}".encode("ascii"))
    h.update(repr(_song_timing_cache_key(calc_song)).encode("utf-8"))
    for key in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate"):
        h.update(bytes(array_sig16(np.asarray(ref_arrays[key], dtype=np.float32).reshape(-1))))
    h.update(str(primary_color or "").encode("utf-8"))
    h.update(b"\0")
    h.update(str(secondary_color or "").encode("utf-8"))
    h.update(b"\0")
    h.update(str(selected_color or "").encode("utf-8"))
    h.update(b"\0")
    h.update(str(int(num_sections)).encode("ascii"))
    h.update(b"\0")
    h.update(str(int(non_fever_base)).encode("ascii"))
    h.update(b"\0")
    h.update(repr(search_ranges).encode("ascii"))
    h.update(b"\0")
    h.update(str(int(solver_version)).encode("ascii"))
    return h.hexdigest()


def base_context_digest(
    *,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    color_flags: dict[str, Any],
    total_budget: int,
    gem_scale_fever: int,
    max_ft_gems: int,
    max_ff_gems: int,
    use_exact_inner_solver: bool,
) -> str:
    h = hashlib.blake2b(digest_size=16)
    h.update(f"base-cache-v{BASE_CACHE_SCHEMA_VERSION}".encode("ascii"))
    h.update(repr(_song_timing_cache_key(calc_song)).encode("utf-8"))
    for key in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate"):
        h.update(bytes(array_sig16(np.asarray(ref_arrays[key], dtype=np.float32).reshape(-1))))
    h.update(str(primary_color or "").encode("utf-8"))
    h.update(b"\0")
    h.update(str(secondary_color or "").encode("utf-8"))
    h.update(b"\0")
    h.update(str(selected_color or "").encode("utf-8"))
    h.update(b"\0")
    for key in (
        "is_p_ft",
        "is_s_ft",
        "is_p_ff",
        "is_s_ff",
        "is_p_pp",
        "is_s_pp",
        "is_p_cm",
        "is_s_cm",
        "is_p_fm",
        "is_s_fm",
        "is_p_ov",
        "is_s_ov",
    ):
        h.update(str(int(color_flags.get(key, 0) or 0)).encode("ascii"))
    h.update(b"\0")
    h.update(str(int(total_budget)).encode("ascii"))
    h.update(b"\0")
    h.update(str(int(gem_scale_fever)).encode("ascii"))
    h.update(b"\0")
    h.update(str(int(max_ft_gems)).encode("ascii"))
    h.update(b"\0")
    h.update(str(int(max_ff_gems)).encode("ascii"))
    h.update(b"\0")
    h.update(b"1" if bool(use_exact_inner_solver) else b"0")
    return h.hexdigest()


def stats7_key(values: tuple[int, ...] | list[int] | np.ndarray) -> tuple[int, ...]:
    out = tuple(int(v) for v in values)
    if len(out) != 7:
        raise ValueError(f"candidate solver cache requires 7 stats, got {len(out)}")
    for value in out:
        if value < -32768 or value > 32767:
            raise ValueError(f"candidate solver cache stat outside int16 range: {value}")
    return out


def _stats_fingerprint(stats: tuple[int, ...]) -> int:
    packed = struct.pack("<7h", *stats)
    return int.from_bytes(hashlib.blake2b(packed, digest_size=8).digest(), "little", signed=False)


def base_stats_hash_key(stats: tuple[int, ...] | list[int] | np.ndarray) -> int:
    out = 2166136261
    for value in stats7_key(stats):
        out = ((int(out) ^ (int(value) + 32769)) * 16777619) & 0xFFFFFFFF
    key = int(out)
    return key if key != 0 else 1


def _path_lock(path: Path) -> threading.Lock:
    resolved = path.resolve()
    with _PATH_LOCKS_GUARD:
        lock = _PATH_LOCKS.get(resolved)
        if lock is None:
            lock = threading.Lock()
            _PATH_LOCKS[resolved] = lock
        return lock


def _pad_i16(values: list[int] | tuple[int, ...], *, n: int) -> tuple[int, ...]:
    if len(values) > int(n):
        raise ValueError(f"FG candidate cache section payload exceeds {n}: {len(values)}")
    out = [int(v) for v in values]
    while len(out) < int(n):
        out.append(0)
    for value in out:
        if value < -32768 or value > 32767:
            raise ValueError(f"FG candidate cache section value outside int16 range: {value}")
    return tuple(out)


def _value_from_result(result: dict[str, Any]) -> FgCandidateCacheValue:
    gem_counts = result.get("gem_counts") if isinstance(result.get("gem_counts"), dict) else {}
    config_counts = list(result.get("config_counts") or [])
    fp_targets = list(result.get("fp_targets") or [])
    num_sections = safe_int(result.get("num_non_fever_sections", len(config_counts)), len(config_counts))
    return FgCandidateCacheValue(
        final_score=safe_int(result.get("final_score", 0), 0),
        base_score=safe_int(result.get("base_score", 0), 0),
        score_penalty=safe_int(result.get("score_penalty", 0), 0),
        fill_penalty=safe_int(result.get("fill_penalty", 0), 0),
        ft=safe_int(result.get("FT", 0), 0),
        ff=safe_int(result.get("FF", 0), 0),
        gems_pp=safe_int(gem_counts.get("Perfect Points", 0), 0),
        gems_cm=safe_int(gem_counts.get("Combo Multiplier", 0), 0),
        gems_fm=safe_int(gem_counts.get("Fever Multiplier", 0), 0),
        gems_ov=safe_int(gem_counts.get("Element", 0), 0),
        num_sections=int(num_sections),
        non_fever_base=safe_int(result.get("non_fever_base", 0), 0),
        config_counts=tuple(int(v) for v in config_counts),
        fp_targets=tuple(int(v) for v in fp_targets),
    )


def _pack_fg_row(stats: tuple[int, ...], value: FgCandidateCacheValue) -> bytes:
    n_sections = int(value.num_sections)
    if n_sections < 0 or n_sections > FG_CACHE_SECTION_CAP:
        raise ValueError(f"FG candidate cache num_sections outside supported range: {n_sections}")
    counts = _pad_i16(value.config_counts, n=FG_CACHE_SECTION_CAP)
    targets = _pad_i16(value.fp_targets, n=FG_CACHE_SECTION_CAP)
    return _FG_ROW.pack(
        _stats_fingerprint(stats),
        *stats,
        int(value.final_score),
        int(value.base_score),
        int(value.score_penalty),
        int(value.fill_penalty),
        int(value.ft),
        int(value.ff),
        int(value.gems_pp),
        int(value.gems_cm),
        int(value.gems_fm),
        int(value.gems_ov),
        int(n_sections),
        int(value.non_fever_base),
        *counts,
        *targets,
    )


def _unpack_fg_row(row: bytes) -> tuple[tuple[int, ...], FgCandidateCacheValue]:
    unpacked = _FG_ROW.unpack(row)
    fingerprint = int(unpacked[0])
    stats = tuple(int(v) for v in unpacked[1:8])
    if _stats_fingerprint(stats) != fingerprint:
        raise ValueError("FG candidate cache row fingerprint mismatch")
    n_sections = int(unpacked[18])
    if n_sections < 0 or n_sections > FG_CACHE_SECTION_CAP:
        raise ValueError(f"FG candidate cache row has invalid section count: {n_sections}")
    counts0 = tuple(int(v) for v in unpacked[20 : 20 + FG_CACHE_SECTION_CAP])
    targets0 = tuple(int(v) for v in unpacked[20 + FG_CACHE_SECTION_CAP : 20 + 2 * FG_CACHE_SECTION_CAP])
    value = FgCandidateCacheValue(
        final_score=int(unpacked[8]),
        base_score=int(unpacked[9]),
        score_penalty=int(unpacked[10]),
        fill_penalty=int(unpacked[11]),
        ft=int(unpacked[12]),
        ff=int(unpacked[13]),
        gems_pp=int(unpacked[14]),
        gems_cm=int(unpacked[15]),
        gems_fm=int(unpacked[16]),
        gems_ov=int(unpacked[17]),
        num_sections=n_sections,
        non_fever_base=int(unpacked[19]),
        config_counts=counts0[:n_sections],
        fp_targets=targets0[:n_sections],
    )
    return stats, value


def _same_value(a: FgCandidateCacheValue, b: FgCandidateCacheValue) -> bool:
    return a == b


def _base_value_from_result8(result8: tuple[int, ...] | list[int] | np.ndarray) -> BaseCandidateCacheValue:
    values = tuple(int(v) for v in result8)
    if len(values) != 8:
        raise ValueError(f"base candidate cache requires 8 result values, got {len(values)}")
    if int(values[0]) < 0:
        raise ValueError("base candidate cache cannot persist invalid score")
    return BaseCandidateCacheValue(
        score=int(values[0]),
        combo_idx=int(values[1]),
        ft=int(values[2]),
        ff=int(values[3]),
        gems_pp=int(values[4]),
        gems_cm=int(values[5]),
        gems_fm=int(values[6]),
        gems_ov=int(values[7]),
    )


def _pack_base_row(stats: tuple[int, ...], value: BaseCandidateCacheValue) -> bytes:
    return _BASE_ROW.pack(
        _stats_fingerprint(stats),
        *stats,
        int(value.score),
        int(value.combo_idx),
        int(value.ft),
        int(value.ff),
        int(value.gems_pp),
        int(value.gems_cm),
        int(value.gems_fm),
        int(value.gems_ov),
    )


def _unpack_base_row(row: bytes) -> tuple[tuple[int, ...], BaseCandidateCacheValue]:
    unpacked = _BASE_ROW.unpack(row)
    fingerprint = int(unpacked[0])
    stats = tuple(int(v) for v in unpacked[1:8])
    if _stats_fingerprint(stats) != fingerprint:
        raise ValueError("base candidate cache row fingerprint mismatch")
    value = BaseCandidateCacheValue(
        score=int(unpacked[8]),
        combo_idx=int(unpacked[9]),
        ft=int(unpacked[10]),
        ff=int(unpacked[11]),
        gems_pp=int(unpacked[12]),
        gems_cm=int(unpacked[13]),
        gems_fm=int(unpacked[14]),
        gems_ov=int(unpacked[15]),
    )
    return stats, value


class FgCandidateCacheShard:
    def __init__(self, path: Path, rows: dict[tuple[int, ...], FgCandidateCacheValue]) -> None:
        self.path = path
        self.rows = dict(rows)

    @classmethod
    def load(cls, context_digest: str) -> "FgCandidateCacheShard":
        path = fg_cache_path(context_digest)
        rows: dict[tuple[int, ...], FgCandidateCacheValue] = {}
        if not path.exists():
            return cls(path, rows)
        payload = path.read_bytes()
        if len(payload) % _FG_ROW.size != 0:
            raise ValueError(f"FG candidate cache file is truncated: {path}")
        for offset in range(0, len(payload), _FG_ROW.size):
            stats, value = _unpack_fg_row(payload[offset : offset + _FG_ROW.size])
            previous = rows.get(stats)
            if previous is not None and not _same_value(previous, value):
                raise ValueError(f"FG candidate cache contains conflicting row for stats={stats}: {path}")
            rows[stats] = value
        return cls(path, rows)

    def get(self, stats: tuple[int, ...] | list[int] | np.ndarray) -> dict[str, Any] | None:
        value = self.rows.get(stats7_key(stats))
        return None if value is None else value.to_result()

    def put(self, stats: tuple[int, ...] | list[int] | np.ndarray, result: dict[str, Any]) -> bool:
        key = stats7_key(stats)
        value = _value_from_result(result)
        existing = self.rows.get(key)
        if existing is not None:
            if not _same_value(existing, value):
                raise ValueError(f"FG candidate cache value changed for stats={key}: {self.path}")
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = _pack_fg_row(key, value)
        lock = _path_lock(self.path)
        with lock:
            with self.path.open("ab") as fh:
                fh.write(row)
        self.rows[key] = value
        return True


class BaseCandidateCacheShard:
    def __init__(self, path: Path, rows: dict[tuple[int, ...], BaseCandidateCacheValue]) -> None:
        self.path = path
        self.rows = dict(rows)

    @classmethod
    def load(cls, context_digest: str) -> "BaseCandidateCacheShard":
        path = base_cache_path(context_digest)
        rows: dict[tuple[int, ...], BaseCandidateCacheValue] = {}
        if not path.exists():
            return cls(path, rows)
        payload = path.read_bytes()
        if len(payload) % _BASE_ROW.size != 0:
            raise ValueError(f"base candidate cache file is truncated: {path}")
        for offset in range(0, len(payload), _BASE_ROW.size):
            stats, value = _unpack_base_row(payload[offset : offset + _BASE_ROW.size])
            previous = rows.get(stats)
            if previous is not None and previous != value:
                raise ValueError(f"base candidate cache contains conflicting row for stats={stats}: {path}")
            rows[stats] = value
        return cls(path, rows)

    def put_result8(
        self,
        stats: tuple[int, ...] | list[int] | np.ndarray,
        result8: tuple[int, ...] | list[int] | np.ndarray,
    ) -> bool:
        key = stats7_key(stats)
        value = _base_value_from_result8(result8)
        if value.combo_idx < 0:
            raise ValueError(f"base candidate cache cannot persist invalid combo index for stats={key}")
        existing = self.rows.get(key)
        if existing is not None:
            if existing != value:
                raise ValueError(
                    "base candidate cache value changed "
                    f"for stats={key}: existing={existing.result8()} new={value.result8()} path={self.path}"
                )
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = _pack_base_row(key, value)
        lock = _path_lock(self.path)
        with lock:
            with self.path.open("ab") as fh:
                fh.write(row)
        self.rows[key] = value
        return True

    def put_result8_rows(
        self,
        stats_rows: np.ndarray,
        result8_rows: np.ndarray,
    ) -> int:
        stats_arr = np.asarray(stats_rows)
        result_arr = np.asarray(result8_rows)
        if stats_arr.ndim != 2 or int(stats_arr.shape[1]) != 7:
            raise ValueError(f"base candidate cache batch stats shape mismatch: {stats_arr.shape} != (n, 7)")
        if result_arr.ndim != 2 or int(result_arr.shape[1]) != 8:
            raise ValueError(f"base candidate cache batch result shape mismatch: {result_arr.shape} != (n, 8)")
        if int(stats_arr.shape[0]) != int(result_arr.shape[0]):
            raise ValueError(
                "base candidate cache batch row count mismatch: "
                f"{stats_arr.shape[0]} != {result_arr.shape[0]}"
            )

        pending: dict[tuple[int, ...], BaseCandidateCacheValue] = {}
        for stats_raw, result_raw in zip(stats_arr, result_arr, strict=True):
            key = stats7_key(stats_raw)
            value = _base_value_from_result8(result_raw)
            if value.combo_idx < 0:
                raise ValueError(f"base candidate cache cannot persist invalid combo index for stats={key}")
            existing = self.rows.get(key)
            if existing is None:
                existing = pending.get(key)
            if existing is not None:
                if existing != value:
                    raise ValueError(
                        "base candidate cache value changed "
                        f"for stats={key}: existing={existing.result8()} new={value.result8()} path={self.path}"
                    )
                continue
            pending[key] = value

        if not pending:
            return 0

        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = bytearray()
        for key, value in pending.items():
            payload.extend(_pack_base_row(key, value))
        lock = _path_lock(self.path)
        with lock:
            with self.path.open("ab") as fh:
                fh.write(payload)
        self.rows.update(pending)
        return int(len(pending))

    def gpu_rows_for_stats(self, stats_rows: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        stats_arr = np.asarray(stats_rows)
        if stats_arr.size == 0:
            return (
                np.zeros((0,), dtype=np.uint32),
                np.zeros((0, 7), dtype=np.int16),
                np.zeros((0, 6), dtype=np.int32),
            )
        if stats_arr.ndim != 2 or int(stats_arr.shape[1]) != 7:
            raise ValueError(f"base candidate cache lookup stats shape mismatch: {stats_arr.shape} != (n, 7)")

        selected_stats: list[tuple[int, ...]] = []
        selected_values: list[BaseCandidateCacheValue] = []
        seen: set[tuple[int, ...]] = set()
        for row in stats_arr:
            key = stats7_key(row)
            if key in seen:
                continue
            seen.add(key)
            value = self.rows.get(key)
            if value is None:
                continue
            selected_stats.append(key)
            selected_values.append(value)

        if not selected_stats:
            return (
                np.zeros((0,), dtype=np.uint32),
                np.zeros((0, 7), dtype=np.int16),
                np.zeros((0, 6), dtype=np.int32),
            )

        out_stats = np.asarray(selected_stats, dtype=np.int16)
        keys = np.asarray([base_stats_hash_key(stats) for stats in selected_stats], dtype=np.uint32)
        results = np.asarray([value.gpu_result6() for value in selected_values], dtype=np.int32)
        return keys, out_stats, results
