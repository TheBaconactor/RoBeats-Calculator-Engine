from __future__ import annotations

import hashlib
import threading
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.constants import FEVER_FILL_BASE_RATE, FEVER_TIME_OFFSET, FEVER_TIME_SCALE, TOTAL_ROWS
from gear_optimizer.core.parsing import env_flag, env_get
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs

from .response_build_gpu import build_force_greats_response_frontiers_gpu_batch
from .response_types import FgResponseFrontierResult, FgResponseSurface

_FG_RESPONSE_CACHE_VERSION = "fg-response-frontier-sparse-bundle-v1"
_MEMORY_CACHE_MAX = max(1, int(env_get("FG_RESPONSE_FRONTIER_MEMORY_CACHE_MAX", "4096") or "4096"))
_PAYLOAD_CACHE_MAX = max(1, int(env_get("FG_RESPONSE_FRONTIER_PAYLOAD_CACHE_MAX", "8") or "8"))
_BUNDLE_ARRAY_CACHE_MAX = max(1, int(env_get("FG_RESPONSE_FRONTIER_BUNDLE_ARRAY_CACHE_MAX", "2") or "2"))
_frontier_cache: OrderedDict[tuple, FgResponseFrontierResult] = OrderedDict()
_payload_cache: OrderedDict[tuple, FgResponseFrontierCachePayload] = OrderedDict()
_bundle_array_cache: OrderedDict[tuple, dict[str, np.ndarray]] = OrderedDict()
_scoring_bundle_cache: OrderedDict[tuple, FgResponseFrontierScoringBundle] = OrderedDict()
_frontier_cache_lock = threading.RLock()
_BUNDLE_KEY_MARKER = "all-stat-keys"
_FIRST_FRONTIER_ONLY_MARKER = "first-frontier-only"


@dataclass(frozen=True, slots=True)
class FgResponseFrontierCachePayload:
    frontier_by_key: dict[tuple[int, int], FgResponseFrontierResult]
    raw_fill_by_ff: np.ndarray
    non_fever_base_by_ff: np.ndarray
    real_time_by_ft: np.ndarray
    total_notes: int
    long_notes: int
    use_forced_great_timing: bool

    def stats_key(self, *, ft_stat: int, ff_stat: int) -> tuple[int, int]:
        return _normalize_stat_key((ft_stat, ff_stat))

    def frontier_for_stats(self, *, ft_stat: int, ff_stat: int) -> FgResponseFrontierResult:
        key = self.stats_key(ft_stat=ft_stat, ff_stat=ff_stat)
        frontier = self.frontier_by_key.get(key)
        if frontier is None:
            raise ValueError(f"FG response frontier stat key was not loaded: {key}")
        return frontier

    def geometry_for_stats(self, *, ft_stat: int, ff_stat: int) -> tuple[float, int, float]:
        ft_i, ff_i = self.stats_key(ft_stat=ft_stat, ff_stat=ff_stat)
        return (
            float(self.raw_fill_by_ff[ff_i]),
            int(self.non_fever_base_by_ff[ff_i]),
            float(self.real_time_by_ft[ft_i]),
        )

    @property
    def frontiers(self) -> tuple[FgResponseFrontierResult, ...]:
        out: list[FgResponseFrontierResult] = []
        seen: set[int] = set()
        for frontier in self.frontier_by_key.values():
            marker = id(frontier)
            if marker in seen:
                continue
            seen.add(marker)
            out.append(frontier)
        return tuple(out)


@dataclass(frozen=True, slots=True)
class FgResponseFrontierCacheInfo:
    cache_key: tuple
    disk_path: Path
    cache_source: str
    total_notes: int
    long_notes: int
    frontier_count: int = 0


@dataclass(frozen=True, slots=True)
class FgResponseFrontierPrewarmResult:
    payload: FgResponseFrontierCachePayload
    cache_key: tuple
    disk_path: Path
    cache_source: str
    elapsed_ms: float
    total_notes: int
    long_notes: int
    frontier_count: int


@dataclass(frozen=True, slots=True)
class FgResponseFrontierScoringBundle:
    frontier_idx_by_key: dict[tuple[int, int], int]
    frontier_idx_by_stat: np.ndarray
    raw_fill_by_ff: np.ndarray
    non_fever_base_by_ff: np.ndarray
    real_time_by_ft: np.ndarray
    surface_words: np.ndarray
    surface_counts: np.ndarray
    frontier_offsets: np.ndarray
    frontier_lengths: np.ndarray
    total_notes: int
    long_notes: int
    use_forced_great_timing: bool


def _normalize_stat_key(stat_key: tuple[int, int] | list[int]) -> tuple[int, int]:
    if len(stat_key) != 2:
        raise ValueError("FG response frontier stat keys must be (ft_stat, ff_stat)")
    ft_stat = max(0, min(TOTAL_ROWS, int(stat_key[0])))
    ff_stat = max(0, min(TOTAL_ROWS, int(stat_key[1])))
    return int(ft_stat), int(ff_stat)


def normalize_fg_response_stat_keys(stat_keys: Iterable[tuple[int, int]] | None) -> tuple[tuple[int, int], ...]:
    keys = tuple(sorted({_normalize_stat_key(key) for key in (stat_keys or ())}))
    if not keys:
        raise ValueError("FG response frontier cache requires at least one FT/FF stat key")
    return keys


def _surface_row(surface: FgResponseSurface) -> tuple[int, ...]:
    return (
        int(surface.fever0),
        int(surface.fever1),
        int(surface.fever2),
        int(surface.fever3),
        int(surface.great0),
        int(surface.great1),
        int(surface.great2),
        int(surface.great3),
        int(surface.body_fever),
        int(surface.body_great),
    )


def _surface_from_row(row: np.ndarray) -> FgResponseSurface:
    values = tuple(int(v) for v in row[:10])
    if len(values) != 10:
        raise ValueError("FG response cache surface row must contain 10 values")
    return FgResponseSurface(*values)


def _surface_from_row_cached(row: np.ndarray, cache: dict[tuple[int, ...], FgResponseSurface]) -> FgResponseSurface:
    values = tuple(int(v) for v in row[:10])
    surface = cache.get(values)
    if surface is None:
        if len(values) != 10:
            raise ValueError("FG response cache surface row must contain 10 values")
        surface = FgResponseSurface(*values)
        cache[values] = surface
    return surface


def fg_response_frontier_song_cache_key(calc_song: dict[str, Any]) -> tuple:
    song_inputs = extract_fg_song_inputs(calc_song)
    timestamps = np.asarray(song_inputs.timestamps, dtype=np.float32).reshape(-1)
    great_candidates = np.asarray(song_inputs.great_candidates, dtype=np.float32).reshape(-1)
    return (
        int(song_inputs.total_notes),
        int(song_inputs.long_notes),
        float(song_inputs.last_note_time),
        bool(song_inputs.use_forced_great_timing),
        bytes(array_sig16(timestamps)),
        bytes(array_sig16(great_candidates)),
    )


def _ref_axes_cache_key(ref_arrays: dict[str, Any]) -> tuple[bytes, bytes]:
    ref_ft = np.asarray(ref_arrays.get("Fever Time", ()), dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_arrays.get("Fever Fill Rate", ()), dtype=np.float32).reshape(-1)
    return bytes(array_sig16(ref_ft)), bytes(array_sig16(ref_ff))


def fg_response_frontier_payload_cache_key(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    stat_keys: Iterable[tuple[int, int]] | None,
) -> tuple:
    return (
        _FG_RESPONSE_CACHE_VERSION,
        fg_response_frontier_song_cache_key(calc_song),
        *_ref_axes_cache_key(ref_arrays),
        normalize_fg_response_stat_keys(stat_keys),
    )


def fg_response_frontier_bundle_cache_key(calc_song: dict[str, Any], ref_arrays: dict[str, Any]) -> tuple:
    return (
        _FG_RESPONSE_CACHE_VERSION,
        fg_response_frontier_song_cache_key(calc_song),
        *_ref_axes_cache_key(ref_arrays),
        _BUNDLE_KEY_MARKER,
    )


def fg_response_frontier_geometry_cache_key(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    ft_stat: int,
    ff_stat: int,
) -> tuple:
    return (
        _FG_RESPONSE_CACHE_VERSION,
        fg_response_frontier_song_cache_key(calc_song),
        *_ref_axes_cache_key(ref_arrays),
        _normalize_stat_key((ft_stat, ff_stat)),
    )


def _fg_response_disk_cache_dir() -> Path:
    override = str(env_get("FG_RESPONSE_FRONTIER_CACHE_DIR", "") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[4] / "bin" / "fg_response_frontier_cache"


def _fg_response_disk_cache_path(cache_key: tuple) -> Path:
    digest = hashlib.blake2b(repr(cache_key).encode("utf-8"), digest_size=16).hexdigest()
    return _fg_response_disk_cache_dir() / f"{digest}.npz"


def _memory_get(cache_key: tuple) -> FgResponseFrontierResult | None:
    with _frontier_cache_lock:
        frontier = _frontier_cache.get(cache_key)
        if frontier is not None:
            _frontier_cache.move_to_end(cache_key)
        return frontier


def _memory_put(cache_key: tuple, frontier: FgResponseFrontierResult) -> None:
    with _frontier_cache_lock:
        _frontier_cache[cache_key] = frontier
        _frontier_cache.move_to_end(cache_key)
        while len(_frontier_cache) > int(_MEMORY_CACHE_MAX):
            _frontier_cache.popitem(last=False)


def _payload_memory_get(cache_key: tuple) -> FgResponseFrontierCachePayload | None:
    with _frontier_cache_lock:
        payload = _payload_cache.get(cache_key)
        if payload is not None:
            _payload_cache.move_to_end(cache_key)
        return payload


def _payload_memory_put(cache_key: tuple, payload: FgResponseFrontierCachePayload) -> None:
    with _frontier_cache_lock:
        _payload_cache[cache_key] = payload
        _payload_cache.move_to_end(cache_key)
        while len(_payload_cache) > int(_PAYLOAD_CACHE_MAX):
            _payload_cache.popitem(last=False)


def reset_fg_response_frontier_payload_cache() -> None:
    with _frontier_cache_lock:
        _frontier_cache.clear()
        _payload_cache.clear()
        _bundle_array_cache.clear()
        _scoring_bundle_cache.clear()


def _pack_frontier(frontier: FgResponseFrontierResult) -> dict[str, np.ndarray]:
    state_items = sorted((int(state), tuple(frontier.state_frontiers[state])) for state in frontier.state_frontiers)
    first_rows = [_surface_row(surface) for surface in frontier.first_frontier]
    state_keys: list[int] = []
    state_surface_offsets: list[int] = []
    state_surface_counts: list[int] = []
    state_surface_rows: list[tuple[int, ...]] = []
    for state, surfaces in state_items:
        state_keys.append(int(state))
        state_surface_offsets.append(len(state_surface_rows))
        state_surface_counts.append(len(surfaces))
        state_surface_rows.extend(_surface_row(surface) for surface in surfaces)
    return {
        "frontier_meta": np.asarray(
            [
                int(frontier.states_evaluated),
                int(frontier.actions),
                int(frontier.transitions_evaluated),
                int(frontier.generated_surfaces),
                int(frontier.retained_surfaces_total),
                int(frontier.max_state_frontier),
                int(frontier.non_fever_base),
            ],
            dtype=np.int32,
        ),
        "first_surface_pool": np.asarray(first_rows, dtype=np.int64).reshape((-1, 10))
        if first_rows
        else np.zeros((0, 10), dtype=np.int64),
        "state_keys": np.asarray(state_keys, dtype=np.int32),
        "state_surface_offsets": np.asarray(state_surface_offsets, dtype=np.int32),
        "state_surface_counts": np.asarray(state_surface_counts, dtype=np.int32),
        "state_surface_pool": np.asarray(state_surface_rows, dtype=np.int64).reshape((-1, 10))
        if state_surface_rows
        else np.zeros((0, 10), dtype=np.int64),
    }


def _unpack_frontier(data: object) -> FgResponseFrontierResult:
    meta = np.asarray(data["frontier_meta"], dtype=np.int32)
    first_pool = np.asarray(data["first_surface_pool"], dtype=np.int64)
    state_keys = np.asarray(data["state_keys"], dtype=np.int32)
    state_surface_offsets = np.asarray(data["state_surface_offsets"], dtype=np.int32)
    state_surface_counts = np.asarray(data["state_surface_counts"], dtype=np.int32)
    state_surface_pool = np.asarray(data["state_surface_pool"], dtype=np.int64)
    states: dict[int, tuple[FgResponseSurface, ...]] = {}
    for idx, state in enumerate(state_keys):
        surface_start = int(state_surface_offsets[idx])
        surface_count = int(state_surface_counts[idx])
        states[int(state)] = tuple(
            _surface_from_row(state_surface_pool[row_idx])
            for row_idx in range(surface_start, surface_start + surface_count)
        )
    return FgResponseFrontierResult(
        first_frontier=tuple(_surface_from_row(row) for row in first_pool),
        state_frontiers=states,
        states_evaluated=int(meta[0]),
        actions=int(meta[1]),
        transitions_evaluated=int(meta[2]),
        generated_surfaces=int(meta[3]),
        retained_surfaces_total=int(meta[4]),
        max_state_frontier=int(meta[5]),
        non_fever_base=int(meta[6]),
        seconds=0.0,
    )


def _pack_frontiers(frontiers: tuple[FgResponseFrontierResult, ...]) -> dict[str, np.ndarray]:
    meta = np.zeros((len(frontiers), 7), dtype=np.int32)
    first_offsets = np.zeros((len(frontiers),), dtype=np.int32)
    first_counts = np.zeros((len(frontiers),), dtype=np.int32)
    state_offsets = np.zeros((len(frontiers),), dtype=np.int32)
    state_counts = np.zeros((len(frontiers),), dtype=np.int32)
    first_rows: list[tuple[int, ...]] = []
    state_keys: list[int] = []
    state_surface_offsets: list[int] = []
    state_surface_counts: list[int] = []
    state_surface_rows: list[tuple[int, ...]] = []

    for idx, frontier in enumerate(frontiers):
        meta[idx] = np.asarray(
            [
                int(frontier.states_evaluated),
                int(frontier.actions),
                int(frontier.transitions_evaluated),
                int(frontier.generated_surfaces),
                int(frontier.retained_surfaces_total),
                int(frontier.max_state_frontier),
                int(frontier.non_fever_base),
            ],
            dtype=np.int32,
        )
        first_offsets[idx] = len(first_rows)
        first_counts[idx] = len(frontier.first_frontier)
        first_rows.extend(_surface_row(surface) for surface in frontier.first_frontier)

        state_offsets[idx] = len(state_keys)
        sorted_states = sorted(int(state) for state in frontier.state_frontiers)
        state_counts[idx] = len(sorted_states)
        for state in sorted_states:
            surfaces = tuple(frontier.state_frontiers[state])
            state_keys.append(int(state))
            state_surface_offsets.append(len(state_surface_rows))
            state_surface_counts.append(len(surfaces))
            state_surface_rows.extend(_surface_row(surface) for surface in surfaces)

    return {
        "frontier_meta": meta,
        "first_offsets": first_offsets,
        "first_counts": first_counts,
        "first_surface_pool": np.asarray(first_rows, dtype=np.int64).reshape((-1, 10))
        if first_rows
        else np.zeros((0, 10), dtype=np.int64),
        "state_offsets": state_offsets,
        "state_counts": state_counts,
        "state_keys": np.asarray(state_keys, dtype=np.int32),
        "state_surface_offsets": np.asarray(state_surface_offsets, dtype=np.int32),
        "state_surface_counts": np.asarray(state_surface_counts, dtype=np.int32),
        "state_surface_pool": np.asarray(state_surface_rows, dtype=np.int64).reshape((-1, 10))
        if state_surface_rows
        else np.zeros((0, 10), dtype=np.int64),
    }


def _unpack_frontiers(data: object, *, include_state_frontiers: bool = True) -> tuple[FgResponseFrontierResult, ...]:
    meta = np.asarray(data["frontier_meta"], dtype=np.int32)
    first_offsets = np.asarray(data["first_offsets"], dtype=np.int32)
    first_counts = np.asarray(data["first_counts"], dtype=np.int32)
    first_pool = np.asarray(data["first_surface_pool"], dtype=np.int64)
    if include_state_frontiers:
        state_offsets = np.asarray(data["state_offsets"], dtype=np.int32)
        state_counts = np.asarray(data["state_counts"], dtype=np.int32)
        state_keys = np.asarray(data["state_keys"], dtype=np.int32)
        state_surface_offsets = np.asarray(data["state_surface_offsets"], dtype=np.int32)
        state_surface_counts = np.asarray(data["state_surface_counts"], dtype=np.int32)
        state_surface_pool = np.asarray(data["state_surface_pool"], dtype=np.int64)

    out: list[FgResponseFrontierResult] = []
    surface_cache: dict[tuple[int, ...], FgResponseSurface] = {}
    for idx in range(int(meta.shape[0])):
        first_start = int(first_offsets[idx])
        first_count = int(first_counts[idx])
        first_frontier = tuple(
            _surface_from_row_cached(first_pool[row_idx], surface_cache)
            for row_idx in range(first_start, first_start + first_count)
        )
        states: dict[int, tuple[FgResponseSurface, ...]] = {}
        if include_state_frontiers:
            state_start = int(state_offsets[idx])
            for pool_idx in range(state_start, state_start + int(state_counts[idx])):
                surface_start = int(state_surface_offsets[pool_idx])
                surface_count = int(state_surface_counts[pool_idx])
                states[int(state_keys[pool_idx])] = tuple(
                    _surface_from_row_cached(state_surface_pool[row_idx], surface_cache)
                    for row_idx in range(surface_start, surface_start + surface_count)
                )
        row = meta[idx]
        out.append(
            FgResponseFrontierResult(
                first_frontier=first_frontier,
                state_frontiers=states,
                states_evaluated=int(row[0]),
                actions=int(row[1]),
                transitions_evaluated=int(row[2]),
                generated_surfaces=int(row[3]),
                retained_surfaces_total=int(row[4]),
                max_state_frontier=int(row[5]),
                non_fever_base=int(row[6]),
                seconds=0.0,
            )
        )
    return tuple(out)


def _unpack_frontier_at(
    data: object,
    frontier_idx: int,
    *,
    include_state_frontiers: bool = True,
) -> FgResponseFrontierResult:
    idx = int(frontier_idx)
    meta = np.asarray(data["frontier_meta"], dtype=np.int32)
    if idx < 0 or idx >= int(meta.shape[0]):
        raise ValueError("FG response cache frontier index is outside the bundle")
    first_offsets = np.asarray(data["first_offsets"], dtype=np.int32)
    first_counts = np.asarray(data["first_counts"], dtype=np.int32)
    first_pool = np.asarray(data["first_surface_pool"], dtype=np.int64)
    surface_cache: dict[tuple[int, ...], FgResponseSurface] = {}

    first_start = int(first_offsets[idx])
    first_count = int(first_counts[idx])
    first_frontier = tuple(
        _surface_from_row_cached(first_pool[row_idx], surface_cache)
        for row_idx in range(first_start, first_start + first_count)
    )
    states: dict[int, tuple[FgResponseSurface, ...]] = {}
    if include_state_frontiers:
        state_offsets = np.asarray(data["state_offsets"], dtype=np.int32)
        state_counts = np.asarray(data["state_counts"], dtype=np.int32)
        state_keys = np.asarray(data["state_keys"], dtype=np.int32)
        state_surface_offsets = np.asarray(data["state_surface_offsets"], dtype=np.int32)
        state_surface_counts = np.asarray(data["state_surface_counts"], dtype=np.int32)
        state_surface_pool = np.asarray(data["state_surface_pool"], dtype=np.int64)
        state_start = int(state_offsets[idx])
        for pool_idx in range(state_start, state_start + int(state_counts[idx])):
            surface_start = int(state_surface_offsets[pool_idx])
            surface_count = int(state_surface_counts[pool_idx])
            states[int(state_keys[pool_idx])] = tuple(
                _surface_from_row_cached(state_surface_pool[row_idx], surface_cache)
                for row_idx in range(surface_start, surface_start + surface_count)
            )
    row = meta[idx]
    return FgResponseFrontierResult(
        first_frontier=first_frontier,
        state_frontiers=states,
        states_evaluated=int(row[0]),
        actions=int(row[1]),
        transitions_evaluated=int(row[2]),
        generated_surfaces=int(row[3]),
        retained_surfaces_total=int(row[4]),
        max_state_frontier=int(row[5]),
        non_fever_base=int(row[6]),
        seconds=0.0,
    )


def _response_axes(calc_song: dict[str, Any], ref_arrays: dict[str, Any]) -> tuple[Any, np.ndarray, np.ndarray, np.ndarray]:
    song_inputs = extract_fg_song_inputs(calc_song)
    ref_ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32).reshape(-1)
    if int(ref_ft.shape[0]) <= TOTAL_ROWS or int(ref_ff.shape[0]) <= TOTAL_ROWS:
        raise ValueError("FG response cache requires full Fever Time and Fever Fill Rate ref arrays")
    base_fill = max(0.0, float(song_inputs.total_notes - int(song_inputs.long_notes)) * float(FEVER_FILL_BASE_RATE))
    base_time = float(song_inputs.last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)
    raw_fill_by_ff = np.asarray([base_fill * float(ref_ff[idx]) for idx in range(TOTAL_ROWS + 1)], dtype=np.float64)
    non_fever_base_by_ff = np.asarray([int(ceil(float(v))) for v in raw_fill_by_ff], dtype=np.int32)
    real_time_by_ft = np.asarray([base_time * float(ref_ft[idx]) for idx in range(TOTAL_ROWS + 1)], dtype=np.float64)
    return song_inputs, raw_fill_by_ff, non_fever_base_by_ff, real_time_by_ft


def _save_payload(cache_key: tuple, payload: FgResponseFrontierCachePayload) -> None:
    if not env_flag("FG_RESPONSE_FRONTIER_DISK_CACHE", "1"):
        return
    path = _fg_response_disk_cache_path(cache_key)
    tmp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp.npz")
        frontiers = payload.frontiers
        frontier_id_by_object = {id(frontier): idx for idx, frontier in enumerate(frontiers)}
        sorted_items = sorted(payload.frontier_by_key.items())
        np.savez_compressed(
            tmp,
            version=np.asarray(_FG_RESPONSE_CACHE_VERSION),
            stat_keys=np.asarray([key for key, _frontier in sorted_items], dtype=np.int32),
            frontier_ids=np.asarray(
                [frontier_id_by_object[id(frontier)] for _key, frontier in sorted_items],
                dtype=np.int32,
            ),
            raw_fill_by_ff=np.asarray(payload.raw_fill_by_ff, dtype=np.float64),
            non_fever_base_by_ff=np.asarray(payload.non_fever_base_by_ff, dtype=np.int32),
            real_time_by_ft=np.asarray(payload.real_time_by_ft, dtype=np.float64),
            total_notes=np.asarray(int(payload.total_notes), dtype=np.int32),
            long_notes=np.asarray(int(payload.long_notes), dtype=np.int32),
            use_forced_great_timing=np.asarray(int(payload.use_forced_great_timing), dtype=np.int8),
            **_pack_frontiers(frontiers),
        )
        tmp.replace(path)
    except Exception:
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        raise


def _load_payload(cache_key: tuple, *, include_state_frontiers: bool = True) -> FgResponseFrontierCachePayload | None:
    if not env_flag("FG_RESPONSE_FRONTIER_DISK_CACHE", "1"):
        return None
    path = _fg_response_disk_cache_path(cache_key)
    if not path.exists():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            version = str(data["version"].item())
            if version != _FG_RESPONSE_CACHE_VERSION:
                return None
            stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
            frontier_ids = np.asarray(data["frontier_ids"], dtype=np.int32)
            frontiers = _unpack_frontiers(data, include_state_frontiers=include_state_frontiers)
            frontier_by_key: dict[tuple[int, int], FgResponseFrontierResult] = {}
            for idx, key_row in enumerate(stat_keys):
                frontier_idx = int(frontier_ids[idx])
                if frontier_idx < 0 or frontier_idx >= len(frontiers):
                    return None
                key = _normalize_stat_key((int(key_row[0]), int(key_row[1])))
                frontier_by_key[key] = frontiers[frontier_idx]
            payload = FgResponseFrontierCachePayload(
                frontier_by_key=frontier_by_key,
                raw_fill_by_ff=np.asarray(data["raw_fill_by_ff"], dtype=np.float64),
                non_fever_base_by_ff=np.asarray(data["non_fever_base_by_ff"], dtype=np.int32),
                real_time_by_ft=np.asarray(data["real_time_by_ft"], dtype=np.float64),
                total_notes=int(np.asarray(data["total_notes"]).item()),
                long_notes=int(np.asarray(data["long_notes"]).item()),
                use_forced_great_timing=bool(int(np.asarray(data["use_forced_great_timing"]).item())),
            )
            if payload.raw_fill_by_ff.shape[0] != TOTAL_ROWS + 1 or payload.real_time_by_ft.shape[0] != TOTAL_ROWS + 1:
                return None
            return payload
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        return None


def _load_bundle_arrays(cache_key: tuple) -> dict[str, np.ndarray]:
    with _frontier_cache_lock:
        cached = _bundle_array_cache.get(cache_key)
        if cached is not None:
            _bundle_array_cache.move_to_end(cache_key)
            return cached
    path = _fg_response_disk_cache_path(cache_key)
    if not path.exists():
        raise ValueError(f"FG response frontier bundle cache is missing: {path}")
    with np.load(path, allow_pickle=False) as data:
        version = str(data["version"].item())
        if version != _FG_RESPONSE_CACHE_VERSION:
            raise ValueError("FG response frontier bundle cache version is invalid")
        arrays = {name: np.asarray(data[name]) for name in data.files if name != "version"}
        arrays["version"] = np.asarray(data["version"])
    with _frontier_cache_lock:
        _bundle_array_cache[cache_key] = arrays
        _bundle_array_cache.move_to_end(cache_key)
        while len(_bundle_array_cache) > int(_BUNDLE_ARRAY_CACHE_MAX):
            _bundle_array_cache.popitem(last=False)
    return arrays


def _source_label(counts: Counter[str]) -> str:
    if int(counts.get("built", 0)) > 0:
        return "built"
    active = [name for name in ("memory", "disk") if int(counts.get(name, 0)) > 0]
    if len(active) == 1:
        return active[0]
    return "mixed" if active else "missing"


def _put_payload_frontiers(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    payload: FgResponseFrontierCachePayload,
) -> None:
    for ft_stat, ff_stat in payload.frontier_by_key:
        _memory_put(
            fg_response_frontier_geometry_cache_key(
                calc_song,
                ref_arrays,
                ft_stat=ft_stat,
                ff_stat=ff_stat,
            ),
            payload.frontier_by_key[(ft_stat, ff_stat)],
        )


def _payload_subset(
    payload: FgResponseFrontierCachePayload,
    keys: Iterable[tuple[int, int]],
) -> FgResponseFrontierCachePayload | None:
    subset: dict[tuple[int, int], FgResponseFrontierResult] = {}
    for key in normalize_fg_response_stat_keys(keys):
        frontier = payload.frontier_by_key.get(key)
        if frontier is None:
            return None
        subset[key] = frontier
    return FgResponseFrontierCachePayload(
        frontier_by_key=subset,
        raw_fill_by_ff=payload.raw_fill_by_ff,
        non_fever_base_by_ff=payload.non_fever_base_by_ff,
        real_time_by_ft=payload.real_time_by_ft,
        total_notes=int(payload.total_notes),
        long_notes=int(payload.long_notes),
        use_forced_great_timing=bool(payload.use_forced_great_timing),
    )


def _payload_missing_keys(
    payload: FgResponseFrontierCachePayload,
    keys: Iterable[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    return tuple(key for key in normalize_fg_response_stat_keys(keys) if key not in payload.frontier_by_key)


def _merge_payloads(
    base: FgResponseFrontierCachePayload | None,
    update: FgResponseFrontierCachePayload,
) -> FgResponseFrontierCachePayload:
    if base is None:
        return update
    frontier_by_key = dict(base.frontier_by_key)
    frontier_by_key.update(update.frontier_by_key)
    return FgResponseFrontierCachePayload(
        frontier_by_key=frontier_by_key,
        raw_fill_by_ff=update.raw_fill_by_ff,
        non_fever_base_by_ff=update.non_fever_base_by_ff,
        real_time_by_ft=update.real_time_by_ft,
        total_notes=int(update.total_notes),
        long_notes=int(update.long_notes),
        use_forced_great_timing=bool(update.use_forced_great_timing),
    )


def build_response_frontier_cache_payload(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    stat_keys: Iterable[tuple[int, int]],
    include_state_frontiers: bool = True,
) -> tuple[FgResponseFrontierCachePayload, str]:
    keys = normalize_fg_response_stat_keys(stat_keys)
    song_inputs, raw_fill_by_ff, non_fever_base_by_ff, real_time_by_ft = _response_axes(calc_song, ref_arrays)
    frontier_by_key: dict[tuple[int, int], FgResponseFrontierResult] = {}
    frontier_by_geometry: dict[tuple[float, int, float, bool], FgResponseFrontierResult] = {}
    missing_by_geometry: dict[tuple[float, int, float, bool], tuple[tuple, tuple[float, int, float]]] = {}
    source_counts: Counter[str] = Counter()
    for ft_stat, ff_stat in keys:
        raw_fill = float(raw_fill_by_ff[ff_stat])
        non_fever_base = int(non_fever_base_by_ff[ff_stat])
        real_fever_time = float(real_time_by_ft[ft_stat])
        geometry_key = (raw_fill, non_fever_base, real_fever_time, bool(song_inputs.use_forced_great_timing))
        frontier = frontier_by_geometry.get(geometry_key)
        source = "memory"
        cache_key = fg_response_frontier_geometry_cache_key(
            calc_song,
            ref_arrays,
            ft_stat=ft_stat,
            ff_stat=ff_stat,
        )
        if frontier is None:
            frontier = _memory_get(cache_key)
        if frontier is None:
            missing_by_geometry.setdefault(
                geometry_key,
                (cache_key, (float(raw_fill), int(non_fever_base), float(real_fever_time))),
            )
            source = "built"
        else:
            frontier_by_geometry[geometry_key] = frontier
        source_counts[source] += 1
    if missing_by_geometry:
        missing_items = tuple(missing_by_geometry.items())
        built_frontiers = build_force_greats_response_frontiers_gpu_batch(
            timestamps=song_inputs.timestamps,
            great_candidate_timestamps=song_inputs.great_candidates,
            geometries=tuple(item[1][1] for item in missing_items),
            use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
            include_state_frontiers=bool(include_state_frontiers),
        )
        if len(built_frontiers) != len(missing_items):
            raise ValueError("FG response frontier GPU batch returned the wrong number of frontiers")
        for (geometry_key, (cache_key, _geometry)), frontier in zip(missing_items, built_frontiers, strict=True):
            _memory_put(cache_key, frontier)
            frontier_by_geometry[geometry_key] = frontier
    for ft_stat, ff_stat in keys:
        raw_fill = float(raw_fill_by_ff[ff_stat])
        non_fever_base = int(non_fever_base_by_ff[ff_stat])
        real_fever_time = float(real_time_by_ft[ft_stat])
        geometry_key = (raw_fill, non_fever_base, real_fever_time, bool(song_inputs.use_forced_great_timing))
        frontier = frontier_by_geometry.get(geometry_key)
        if frontier is None:
            raise ValueError(f"FG response frontier geometry was not built: {geometry_key!r}")
        _memory_put(
            fg_response_frontier_geometry_cache_key(
                calc_song,
                ref_arrays,
                ft_stat=ft_stat,
                ff_stat=ff_stat,
            ),
            frontier,
        )
        frontier_by_key[(int(ft_stat), int(ff_stat))] = frontier
    payload = FgResponseFrontierCachePayload(
        frontier_by_key=frontier_by_key,
        raw_fill_by_ff=raw_fill_by_ff,
        non_fever_base_by_ff=non_fever_base_by_ff,
        real_time_by_ft=real_time_by_ft,
        total_notes=int(song_inputs.total_notes),
        long_notes=int(song_inputs.long_notes),
        use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
    )
    return payload, _source_label(source_counts)


def fg_response_frontier_payload_cache_info(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    stat_keys: Iterable[tuple[int, int]],
) -> FgResponseFrontierCacheInfo:
    keys = normalize_fg_response_stat_keys(stat_keys)
    payload_key = fg_response_frontier_payload_cache_key(calc_song, ref_arrays, keys)
    bundle_key = fg_response_frontier_bundle_cache_key(calc_song, ref_arrays)
    payload = _payload_memory_get(payload_key)
    if payload is not None:
        return FgResponseFrontierCacheInfo(
            cache_key=payload_key,
            disk_path=_fg_response_disk_cache_path(payload_key),
            cache_source="memory",
            total_notes=int(payload.total_notes),
            long_notes=int(payload.long_notes),
            frontier_count=int(len(payload.frontier_by_key)),
        )
    if env_flag("FG_RESPONSE_FRONTIER_DISK_CACHE", "1") and _fg_response_disk_cache_path(payload_key).exists():
        song_inputs = extract_fg_song_inputs(calc_song)
        return FgResponseFrontierCacheInfo(
            cache_key=payload_key,
            disk_path=_fg_response_disk_cache_path(payload_key),
            cache_source="disk",
            total_notes=int(song_inputs.total_notes),
            long_notes=int(song_inputs.long_notes),
            frontier_count=int(len(keys)),
        )
    bundle = _payload_memory_get(bundle_key)
    if bundle is None and env_flag("FG_RESPONSE_FRONTIER_DISK_CACHE", "1"):
        bundle = _load_payload(bundle_key)
    if bundle is not None:
        subset = _payload_subset(bundle, keys)
        if subset is not None:
            return FgResponseFrontierCacheInfo(
                cache_key=payload_key,
                disk_path=_fg_response_disk_cache_path(bundle_key),
                cache_source="disk",
                total_notes=int(subset.total_notes),
                long_notes=int(subset.long_notes),
                frontier_count=int(len(subset.frontier_by_key)),
            )
    source_counts: Counter[str] = Counter()
    for ft_stat, ff_stat in keys:
        cache_key = fg_response_frontier_geometry_cache_key(
            calc_song,
            ref_arrays,
            ft_stat=ft_stat,
            ff_stat=ff_stat,
        )
        if _memory_get(cache_key) is not None:
            source_counts["memory"] += 1
        else:
            source_counts["missing"] += 1
    song_inputs = extract_fg_song_inputs(calc_song)
    return FgResponseFrontierCacheInfo(
        cache_key=payload_key,
        disk_path=_fg_response_disk_cache_path(payload_key),
        cache_source=_source_label(source_counts),
        total_notes=int(song_inputs.total_notes),
        long_notes=int(song_inputs.long_notes),
        frontier_count=int(len(keys) - int(source_counts.get("missing", 0))),
    )


def load_response_frontier_from_bundle(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    ft_stat: int,
    ff_stat: int,
) -> FgResponseFrontierResult:
    key = _normalize_stat_key((ft_stat, ff_stat))
    cache_key = fg_response_frontier_geometry_cache_key(calc_song, ref_arrays, ft_stat=key[0], ff_stat=key[1])
    frontier = _memory_get(cache_key)
    if frontier is not None and frontier.state_frontiers:
        return frontier
    bundle_key = fg_response_frontier_bundle_cache_key(calc_song, ref_arrays)
    data = _load_bundle_arrays(bundle_key)
    stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
    matches = np.nonzero((stat_keys[:, 0] == int(key[0])) & (stat_keys[:, 1] == int(key[1])))[0]
    if int(matches.shape[0]) <= 0:
        raise ValueError(f"FG response frontier bundle cache is missing stat key: {key}")
    frontier_ids = np.asarray(data["frontier_ids"], dtype=np.int32)
    frontier = _unpack_frontier_at(data, int(frontier_ids[int(matches[0])]), include_state_frontiers=True)
    if not frontier.state_frontiers:
        payload, _source = build_response_frontier_cache_payload(
            calc_song,
            ref_arrays,
            stat_keys=(key,),
            include_state_frontiers=True,
        )
        bundle_key = fg_response_frontier_bundle_cache_key(calc_song, ref_arrays)
        bundle = _merge_payloads(_load_payload(bundle_key, include_state_frontiers=True), payload)
        _save_payload(bundle_key, bundle)
        with _frontier_cache_lock:
            _bundle_array_cache.pop(bundle_key, None)
            _scoring_bundle_cache.pop(bundle_key, None)
        frontier = payload.frontier_for_stats(ft_stat=int(key[0]), ff_stat=int(key[1]))
    _memory_put(cache_key, frontier)
    return frontier


def build_or_load_response_frontier_scoring_bundle(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    stat_keys: Iterable[tuple[int, int]],
) -> FgResponseFrontierScoringBundle:
    keys = normalize_fg_response_stat_keys(stat_keys)
    bundle_key = fg_response_frontier_bundle_cache_key(calc_song, ref_arrays)
    bundle: FgResponseFrontierCachePayload | None = None
    arrays: dict[str, np.ndarray] | None = None
    try:
        arrays = _load_bundle_arrays(bundle_key)
    except ValueError:
        arrays = None
    if arrays is not None:
        available = {
            _normalize_stat_key((int(row[0]), int(row[1])))
            for row in np.asarray(arrays["stat_keys"], dtype=np.int32)
        }
        missing = tuple(key for key in keys if key not in available)
        if missing:
            bundle = _load_payload(bundle_key, include_state_frontiers=True)
            missing_payload, _source = build_response_frontier_cache_payload(
                calc_song,
                ref_arrays,
                stat_keys=missing,
                include_state_frontiers=False,
            )
            bundle = _merge_payloads(bundle, missing_payload)
            _save_payload(bundle_key, bundle)
            with _frontier_cache_lock:
                _bundle_array_cache.pop(bundle_key, None)
                _scoring_bundle_cache.pop(bundle_key, None)
            arrays = _load_bundle_arrays(bundle_key)
    else:
        build_or_load_response_frontier_payload(
            calc_song,
            ref_arrays,
            stat_keys=keys,
            include_state_frontiers=False,
        )
        arrays = _load_bundle_arrays(bundle_key)

    with _frontier_cache_lock:
        cached_scoring = _scoring_bundle_cache.get(bundle_key)
        if cached_scoring is not None:
            if len(cached_scoring.frontier_idx_by_key) >= (TOTAL_ROWS + 1) * (TOTAL_ROWS + 1) or all(
                key in cached_scoring.frontier_idx_by_key for key in keys
            ):
                _scoring_bundle_cache.move_to_end(bundle_key)
                return cached_scoring

    stat_key_rows = np.asarray(arrays["stat_keys"], dtype=np.int32)
    frontier_ids = np.asarray(arrays["frontier_ids"], dtype=np.int32)
    frontier_idx_by_key: dict[tuple[int, int], int] = {}
    requested = set(keys)
    for idx, row in enumerate(stat_key_rows):
        key = _normalize_stat_key((int(row[0]), int(row[1])))
        if key in requested:
            frontier_idx_by_key[key] = int(frontier_ids[int(idx)])
    if len(frontier_idx_by_key) != len(keys):
        missing = sorted(set(keys) - set(frontier_idx_by_key))
        raise ValueError(f"FG response frontier scoring bundle is missing stat keys: {missing[:5]!r}")

    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    for key, frontier_idx in frontier_idx_by_key.items():
        frontier_idx_by_stat[int(key[0]), int(key[1])] = int(frontier_idx)
    first_pool = np.asarray(arrays["first_surface_pool"], dtype=np.int64)
    surface_words = np.ascontiguousarray(first_pool[:, :8], dtype=np.uint32)
    surface_counts = np.ascontiguousarray(first_pool[:, 8:10], dtype=np.int32)
    scoring_bundle = FgResponseFrontierScoringBundle(
        frontier_idx_by_key=frontier_idx_by_key,
        frontier_idx_by_stat=frontier_idx_by_stat,
        raw_fill_by_ff=np.asarray(arrays["raw_fill_by_ff"], dtype=np.float64),
        non_fever_base_by_ff=np.asarray(arrays["non_fever_base_by_ff"], dtype=np.int32),
        real_time_by_ft=np.asarray(arrays["real_time_by_ft"], dtype=np.float64),
        surface_words=surface_words,
        surface_counts=surface_counts,
        frontier_offsets=np.asarray(arrays["first_offsets"], dtype=np.int32),
        frontier_lengths=np.asarray(arrays["first_counts"], dtype=np.int32),
        total_notes=int(np.asarray(arrays["total_notes"]).item()),
        long_notes=int(np.asarray(arrays["long_notes"]).item()),
        use_forced_great_timing=bool(int(np.asarray(arrays["use_forced_great_timing"]).item())),
    )
    with _frontier_cache_lock:
        _scoring_bundle_cache[bundle_key] = scoring_bundle
        _scoring_bundle_cache.move_to_end(bundle_key)
        while len(_scoring_bundle_cache) > int(_BUNDLE_ARRAY_CACHE_MAX):
            _scoring_bundle_cache.popitem(last=False)
    return scoring_bundle


def build_or_load_response_frontier_payload(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    stat_keys: Iterable[tuple[int, int]],
    include_state_frontiers: bool = True,
) -> FgResponseFrontierPrewarmResult:
    started = time.perf_counter()
    keys = normalize_fg_response_stat_keys(stat_keys)
    cache_key = fg_response_frontier_payload_cache_key(calc_song, ref_arrays, keys)
    bundle_key = fg_response_frontier_bundle_cache_key(calc_song, ref_arrays)
    bundle_path = _fg_response_disk_cache_path(bundle_key)
    memory_key = cache_key if include_state_frontiers else (*cache_key, _FIRST_FRONTIER_ONLY_MARKER)
    bundle_memory_key = bundle_key if include_state_frontiers else (*bundle_key, _FIRST_FRONTIER_ONLY_MARKER)
    payload = _payload_memory_get(memory_key)
    if payload is not None:
        return FgResponseFrontierPrewarmResult(
            payload=payload,
            cache_key=cache_key,
            disk_path=bundle_path,
            cache_source="memory",
            elapsed_ms=float((time.perf_counter() - started) * 1000.0),
            total_notes=int(payload.total_notes),
            long_notes=int(payload.long_notes),
            frontier_count=int(len(payload.frontiers)),
        )
    source = "disk"
    payload = _load_payload(cache_key, include_state_frontiers=include_state_frontiers)
    bundle: FgResponseFrontierCachePayload | None = None
    if payload is None:
        bundle = _payload_memory_get(bundle_memory_key)
        if bundle is None:
            bundle = _load_payload(bundle_key, include_state_frontiers=include_state_frontiers)
        if bundle is not None:
            payload = _payload_subset(bundle, keys)
        if payload is None:
            if bundle is not None and not include_state_frontiers:
                bundle = _load_payload(bundle_key, include_state_frontiers=True)
            missing_keys = _payload_missing_keys(bundle, keys) if bundle is not None else keys
            payload, source = build_response_frontier_cache_payload(
                calc_song,
                ref_arrays,
                stat_keys=missing_keys,
                include_state_frontiers=bool(include_state_frontiers),
            )
            bundle = _merge_payloads(bundle, payload)
            _save_payload(bundle_key, bundle)
            _payload_memory_put(bundle_key, bundle)
            payload = _payload_subset(bundle, keys)
            if payload is None:
                raise ValueError("FG response frontier bundle did not contain requested keys after build")
        else:
            source = "disk"
    elif include_state_frontiers:
        bundle = _merge_payloads(_load_payload(bundle_key), payload)
        _save_payload(bundle_key, bundle)
        _payload_memory_put(bundle_key, bundle)
    _payload_memory_put(memory_key, payload)
    _put_payload_frontiers(calc_song, ref_arrays, payload)
    return FgResponseFrontierPrewarmResult(
        payload=payload,
        cache_key=cache_key,
        disk_path=bundle_path,
        cache_source=source,
        elapsed_ms=float((time.perf_counter() - started) * 1000.0),
        total_notes=int(payload.total_notes),
        long_notes=int(payload.long_notes),
        frontier_count=int(len(payload.frontiers)),
    )


def cleanup_fg_response_frontier_cache_temp_files(cache_dir: str | Path | None = None) -> int:
    root = Path(cache_dir) if cache_dir is not None else _fg_response_disk_cache_dir()
    if not root.exists():
        return 0
    removed = 0
    for path in root.glob("*.tmp.npz"):
        path.unlink(missing_ok=True)
        removed += 1
    return int(removed)


__all__ = [
    "FgResponseFrontierCacheInfo",
    "FgResponseFrontierCachePayload",
    "FgResponseFrontierPrewarmResult",
    "FgResponseFrontierScoringBundle",
    "_FG_RESPONSE_CACHE_VERSION",
    "_fg_response_disk_cache_path",
    "build_or_load_response_frontier_payload",
    "build_or_load_response_frontier_scoring_bundle",
    "build_response_frontier_cache_payload",
    "cleanup_fg_response_frontier_cache_temp_files",
    "fg_response_frontier_bundle_cache_key",
    "fg_response_frontier_geometry_cache_key",
    "fg_response_frontier_payload_cache_info",
    "fg_response_frontier_payload_cache_key",
    "load_response_frontier_from_bundle",
    "normalize_fg_response_stat_keys",
    "reset_fg_response_frontier_payload_cache",
]
