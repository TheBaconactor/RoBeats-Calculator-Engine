from __future__ import annotations

import dataclasses
import time
from pathlib import Path

import numpy as np

from gear_optimizer.core.file_lock import exclusive_file_lock
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.timing_envelope import TimedSong

from .fg_cache_keys import _response_axes, fg_response_frontier_bundle_cache_key
from .fg_cache_patterns import surface_head_greats, unpack_surface_patterns
from .fg_cache_store import (
    FG_RESPONSE_FRONTIER_CACHE,
    _load_payload,
    _payload_file_is_complete,
    _response_bundle_build_slot,
    _save_payload,
    _scoring_bundle_memory,
    read_compatible_bundle,
)
from .fg_cache_types import (
    FgResponseFrontierCachePayload,
    FgResponseFrontierScoringBundle,
    all_response_stat_keys,
)
from .producer_batch import build_frontiers, song_arrays
from .producer_kernels import _HEAD_DOM_B, _HEAD_DOM_C, _HEAD_DOM_F
from .types import SurfacePool


def _missing_payload_keys(payload: FgResponseFrontierCachePayload | None, keys: np.ndarray) -> np.ndarray:
    """The rows of `keys` the payload holds no surfaces for."""
    if payload is None:
        return keys
    held = payload.frontier_by_key
    missing = [key for key in keys.tolist() if not (tuple(key) in held and held[tuple(key)].first_frontier)]
    return np.asarray(missing, dtype=np.int32).reshape(-1, 2)


def _merge_payloads(
    base: FgResponseFrontierCachePayload | None,
    update: FgResponseFrontierCachePayload,
) -> FgResponseFrontierCachePayload:
    if base is None:
        return update
    return dataclasses.replace(update, frontier_by_key={**base.frontier_by_key, **update.frontier_by_key})


def _assert_head_dominance_box_covers(curves: StatCurves) -> None:
    """Fail loud if a gear rebalance pushes a curve outside the lossless cone filters' box (_HEAD_DOM_B/C/F): their proof
    holds ONLY while the box is a superset of the realizable values, so a stale box must never silently under-cover. Reads
    the float32 curves the solve uses."""
    for name, (low, high) in (
        ("Perfect Points", _HEAD_DOM_B), ("Combo Multiplier", _HEAD_DOM_C), ("Fever Multiplier", _HEAD_DOM_F),
    ):
        curve = np.asarray(curves.f32[name], dtype=np.float64)
        if not (low <= float(curve.min()) and float(curve.max()) <= high):
            raise ValueError(
                f"FG cone-filter box {name} ({low}, {high}) no longer covers the gear's [{float(curve.min()):.4f}, "
                f"{float(curve.max()):.4f}]: update _HEAD_DOM_* in producer_kernels.py"
            )


def _build_response_frontier_cache_payload(
    song: TimedSong,
    curves: StatCurves,
    stat_keys: np.ndarray,
) -> FgResponseFrontierCachePayload:
    """The frontiers of `stat_keys` (sorted), one per distinct fever geometry, in ONE batch call: the batch entry owns
    region-core-table admission and reduction, and every song-invariant input is built exactly once per song."""
    _assert_head_dominance_box_covers(curves)
    song_inputs, raw_fill_by_ff, non_fever_base_by_ff, real_time_by_ft = _response_axes(song, curves)
    geometry_of = {
        (ft_stat, ff_stat): (float(raw_fill_by_ff[ff_stat]), int(non_fever_base_by_ff[ff_stat]), float(real_time_by_ft[ft_stat]))
        for ft_stat, ff_stat in stat_keys.tolist()
    }
    geometries = tuple(dict.fromkeys(geometry_of.values()))
    built = build_frontiers(
        song_arrays(
            song_inputs.timestamps, song_inputs.perfect_candidates, song_inputs.great_candidates,
            song_inputs.perfect_floor, song_inputs.great_floor, song_inputs.late_great_floor,
            song_inputs.exit_ceiling, song_inputs.lanes,
        ),
        geometries,
        bool(song_inputs.use_forced_great_timing),
    )
    if not all(frontier.first_frontier for frontier in built):
        raise ValueError("FG response frontier cache requires first-frontier surfaces")
    frontier_of = dict(zip(geometries, built, strict=True))
    return FgResponseFrontierCachePayload(
        frontier_by_key={key: frontier_of[geometry] for key, geometry in geometry_of.items()},
        raw_fill_by_ff=raw_fill_by_ff,
        non_fever_base_by_ff=non_fever_base_by_ff,
        real_time_by_ft=real_time_by_ft,
        total_notes=int(song_inputs.total_notes),
        long_notes=int(song_inputs.long_notes),
        use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
    )


def _scoring_bundle(cache_key: tuple, arrays: dict[str, np.ndarray]) -> FgResponseFrontierScoringBundle:
    """A bundle file's arrays (store.read_compatible_bundle) as a scoring bundle over every stat key it holds."""
    stat_key_rows = np.asarray(arrays["stat_keys"], dtype=np.int32).reshape((-1, 2))
    frontier_idx_by_stat = np.full((MAX_STAT + 1, MAX_STAT + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[stat_key_rows[:, 0], stat_key_rows[:, 1]] = np.asarray(arrays["frontier_ids"], dtype=np.int32)
    total_notes = int(arrays["total_notes"].item())
    if int(arrays["first_surface_head_len"].item()) != min(total_notes, 100):
        raise ValueError("FG response frontier scoring bundle has invalid surface head coefficient metadata")
    rows, patterns = arrays["surface_rows"], arrays["surface_patterns"]
    pattern_ids = np.asarray(rows[0], dtype=np.int32)
    if pattern_ids.size and not 0 <= int(pattern_ids.min()) <= int(pattern_ids.max()) < patterns.shape[1]:
        raise ValueError("FG response surface row references an invalid head-pattern ID")
    pattern_words, head_coeffs = unpack_surface_patterns(patterns.T)
    return FgResponseFrontierScoringBundle(
        cache_key=cache_key,
        frontier_idx_by_stat=frontier_idx_by_stat,
        raw_fill_by_ff=np.asarray(arrays["raw_fill_by_ff"], dtype=np.float64),
        non_fever_base_by_ff=np.asarray(arrays["non_fever_base_by_ff"], dtype=np.int32),
        real_time_by_ft=np.asarray(arrays["real_time_by_ft"], dtype=np.float64),
        pool=SurfacePool(
            frontier_offsets=np.asarray(arrays["first_offsets"], dtype=np.int32),
            frontier_lengths=np.asarray(arrays["first_counts"], dtype=np.int32),
            pattern_ids=pattern_ids,
            pattern_words=pattern_words,
            counts=np.ascontiguousarray(rows[1:4].T, dtype=np.int32),
            head_coeffs=head_coeffs,
            head_greats=surface_head_greats(pattern_words),
        ),
        total_notes=total_notes,
        long_notes=int(arrays["long_notes"].item()),
        use_forced_great_timing=bool(int(arrays["use_forced_great_timing"].item())),
    )


def _missing_stat_keys(bundle: FgResponseFrontierScoringBundle, keys: np.ndarray) -> np.ndarray:
    """The rows of `keys` the bundle does not hold."""
    return keys[bundle.frontier_idx_by_stat[keys[:, 0], keys[:, 1]] < 0]


def load_response_frontier_scoring_bundle(
    song: TimedSong,
    curves: StatCurves,
    *,
    stat_keys: np.ndarray | None = None,
) -> FgResponseFrontierScoringBundle:
    """The song's scoring bundle (its whole file) holding `stat_keys`, an (n, 2) array (default: every FT/FF key). A
    bundle held in memory that lacks some is read again: another process may have extended the file."""
    keys = all_response_stat_keys() if stat_keys is None else stat_keys
    bundle_key = fg_response_frontier_bundle_cache_key(song, curves)
    cached = _scoring_bundle_memory.get(bundle_key)
    if cached is not None and not len(_missing_stat_keys(cached, keys)):
        return cached
    arrays = read_compatible_bundle(bundle_key)
    if arrays is None:
        raise ValueError(
            "FG response frontier scoring bundle is missing. Startup cache prebuild must build "
            "the candidate-independent all-FT/FF bundle before runtime scoring."
        )
    scoring_bundle = _scoring_bundle(bundle_key, arrays)
    missing = _missing_stat_keys(scoring_bundle, keys)
    if len(missing):
        raise ValueError(
            "FG response frontier scoring bundle does not cover requested stat keys. "
            "Startup cache prebuild must build the candidate-independent all-FT/FF bundle before runtime scoring: "
            f"{missing[:5].tolist()!r}"
        )
    _scoring_bundle_memory.put(bundle_key, scoring_bundle)
    return scoring_bundle


def ensure_response_frontier_cache_for_song(
    song: TimedSong,
    curves: StatCurves,
    *,
    stat_keys: np.ndarray | None = None,
) -> tuple[str, float, Path]:
    """Make sure the song's bundle file holds `stat_keys`, a sorted (n, 2) array (default: every FT/FF key); returns
    (cache source, build ms, bundle file). The bundle is keyed by the song's timing, so a chart-only (non-precise) song
    has its own, distinct from the precise one.

    A hit costs a metadata probe. A miss extends the file with disk as the authoritative base, while one cross-process
    owner holds the read-merge-publish transaction (another process may have published a larger bundle meanwhile)."""
    keys = all_response_stat_keys() if stat_keys is None else stat_keys
    bundle_key = fg_response_frontier_bundle_cache_key(song, curves)
    if _payload_file_is_complete(FG_RESPONSE_FRONTIER_CACHE.serving_path(bundle_key), keys):
        return "disk", 0.0, FG_RESPONSE_FRONTIER_CACHE.serving_path(bundle_key)
    started = time.perf_counter()
    source = "disk"
    bundle_path = FG_RESPONSE_FRONTIER_CACHE.file_path(bundle_key)
    with _response_bundle_build_slot, exclusive_file_lock(bundle_path.parent / ".bundle_locks" / bundle_path.stem):
        bundle = _load_payload(bundle_key)
        missing = _missing_payload_keys(bundle, keys)
        if len(missing):
            _save_payload(bundle_key, _merge_payloads(bundle, _build_response_frontier_cache_payload(song, curves, missing)))
            _scoring_bundle_memory.pop(bundle_key)
            source = "built"
    return source, (time.perf_counter() - started) * 1000.0, FG_RESPONSE_FRONTIER_CACHE.serving_path(bundle_key)


def scoring_bundle_covering(song: TimedSong, curves: StatCurves, stat_keys: np.ndarray) -> FgResponseFrontierScoringBundle:
    """The song's scoring bundle holding `stat_keys`, the cells a file lacks built first."""
    cached = _scoring_bundle_memory.get(fg_response_frontier_bundle_cache_key(song, curves))
    if cached is not None and not len(_missing_stat_keys(cached, stat_keys)):
        return cached
    ensure_response_frontier_cache_for_song(song, curves, stat_keys=stat_keys)
    return load_response_frontier_scoring_bundle(song, curves, stat_keys=stat_keys)
