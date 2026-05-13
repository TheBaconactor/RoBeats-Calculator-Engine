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
from gear_optimizer.core.utils import safe_int
from gear_optimizer.solver.scoring.stats_scoring import _force_greats_counts_to_dict
from gear_optimizer.solver.taichi_gem.api.timeline import _song_timing_cache_key


FG_CACHE_SCHEMA_VERSION = 1
FG_CACHE_SECTION_CAP = 20
_FG_ROW = struct.Struct("<Q7hiiiiBBBBBBBI20h20h")
_PATH_LOCKS: dict[Path, threading.Lock] = {}
_PATH_LOCKS_GUARD = threading.Lock()


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


def solver_candidate_cache_root() -> Path:
    return Path(PATHS.bin_dir) / "solver_candidate_cache"


def fg_cache_path(context_digest: str) -> Path:
    digest = str(context_digest or "").strip()
    if len(digest) != 32:
        raise ValueError(f"invalid FG candidate cache digest: {context_digest!r}")
    return solver_candidate_cache_root() / "fg" / f"{digest}.bin"


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
