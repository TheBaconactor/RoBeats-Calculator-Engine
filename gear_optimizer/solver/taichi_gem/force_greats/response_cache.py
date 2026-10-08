from __future__ import annotations

import time
from collections import Counter
from pathlib import Path
from typing import Iterable

import numpy as np

from gear_optimizer.solver.timing_envelope import TimedSong
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.frontier_cache import FrontierCacheInfo, FrontierCacheLoad
from gear_optimizer.solver.frontier_cache_build_lock import FrontierBuildLock

from .response_build_gpu_batch import build_force_greats_response_first_frontiers_gpu_batch
from .response_build_gpu_numba import _HEAD_DOM_C, _HEAD_DOM_F, _HEAD_DOM_G, _HEAD_DOM_V, _numba_session_box_keep_mask
from .response_cache_keys import (
    _response_axes,
    fg_response_frontier_bundle_cache_key,
    fg_response_frontier_payload_cache_key,
)
from .response_cache_store import (
    FG_RESPONSE_FRONTIER_CACHE,
    _dense_rank_pattern_ids_inplace,
    _frontier_is_complete,
    _load_payload,
    _payload_disk_is_complete,
    _payload_memory,
    _response_bundle_build_slots,
    _save_payload,
    _scoring_bundle_memory,
    gather_surface_patterns,
    read_compatible_bundle,
    release_fg_response_song_memory,
)
from .response_cache_types import (
    FgResponseFrontierCachePayload,
    FgResponseFrontierScoringBundle,
    all_response_stat_keys,
    normalize_fg_response_stat_keys,
)
from .response_types import FgResponseFrontierResult

def _source_label(counts: Counter[str]) -> str:
    if int(counts.get("built", 0)) > 0:
        return "built"
    active = [name for name in ("memory", "disk") if int(counts.get(name, 0)) > 0]
    if len(active) == 1:
        return active[0]
    return "mixed" if active else "missing"


def _response_bundle_build_lock(bundle_key: tuple) -> FrontierBuildLock:
    bundle_path = FG_RESPONSE_FRONTIER_CACHE.file_path(bundle_key)
    lock_dir = bundle_path.parent / ".bundle_locks" / bundle_path.stem
    return FrontierBuildLock(lock_dir, label=f"fg_response_bundle:{bundle_path.stem}")


def _payload_subset(
    payload: FgResponseFrontierCachePayload | None,
    keys: Iterable[tuple[int, int]],
) -> FgResponseFrontierCachePayload | None:
    if payload is None:
        return None
    subset: dict[tuple[int, int], FgResponseFrontierResult] = {}
    for key in normalize_fg_response_stat_keys(keys):
        frontier = payload.frontier_by_key.get(key)
        if not _frontier_is_complete(frontier):
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


def _payload_missing_or_incomplete_keys(
    payload: FgResponseFrontierCachePayload | None,
    keys: Iterable[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    out: list[tuple[int, int]] = []
    for key in normalize_fg_response_stat_keys(keys):
        frontier = None if payload is None else payload.frontier_by_key.get(key)
        if not _frontier_is_complete(frontier):
            out.append(key)
    return tuple(out)


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


def _assert_head_dominance_box_covers(curves: StatCurves) -> None:
    """Fail loud if a gear rebalance pushes the combo/fever multipliers outside the lossless
    head-dominance box (_HEAD_DOM_C/_HEAD_DOM_F). The 16-corner prune is exact ONLY while the box is
    a superset of the realizable (c, f) cone, so a stale box must never silently under-cover. Reads
    the float32 curves the solve uses."""
    cm = np.asarray(curves.f32["Combo Multiplier"], dtype=np.float64)
    fm = np.asarray(curves.f32["Fever Multiplier"], dtype=np.float64)
    if not (_HEAD_DOM_C[0] <= float(cm.min()) and float(cm.max()) <= _HEAD_DOM_C[1]
            and _HEAD_DOM_F[0] <= float(fm.min()) and float(fm.max()) <= _HEAD_DOM_F[1]):
        raise ValueError(
            f"FG head-dominance box combo{_HEAD_DOM_C} fever{_HEAD_DOM_F} no longer covers the gear's "
            f"combo-mul [{float(cm.min()):.4f},{float(cm.max()):.4f}] / fever-mul "
            f"[{float(fm.min()):.4f},{float(fm.max()):.4f}] -- update _HEAD_DOM_C/_HEAD_DOM_F in "
            f"response_build_gpu_numba.py (the lossless head prune requires the box to be a superset)."
        )


def session_head_dominance_box(curves: StatCurves) -> tuple[float, float, float, float, float, float, float, float]:
    """The SESSION's 16-corner dominance box: combo/fever corners tightened to the inventory's
    measured LUT ranges (the same arrays `_assert_head_dominance_box_covers` validates), value and
    great corners kept at the global box (v1: their per-note derivation is color-coupled; the
    global corners stay a sound cover). Reads the float32 curves the solve uses."""
    cm = np.asarray(curves.f32["Combo Multiplier"], dtype=np.float64)
    fm = np.asarray(curves.f32["Fever Multiplier"], dtype=np.float64)
    c_lo, c_hi = float(cm.min()), float(cm.max())
    f_lo, f_hi = float(fm.min()), float(fm.max())
    # The payload's envelope was pruned against the GLOBAL box; a session box escaping it means the
    # payload never covered these cells -- the same invariant _assert_head_dominance_box_covers
    # enforces at build time. Never widen silently.
    if c_lo < float(_HEAD_DOM_C[0]) or c_hi > float(_HEAD_DOM_C[1]) or f_lo < float(_HEAD_DOM_F[0]) or f_hi > float(_HEAD_DOM_F[1]):
        raise ValueError(
            f"session dominance box combo[{c_lo:.4f},{c_hi:.4f}] fever[{f_lo:.4f},{f_hi:.4f}] escapes the "
            f"global box combo{_HEAD_DOM_C} fever{_HEAD_DOM_F} the payload envelope was built against"
        )
    return (
        float(_HEAD_DOM_V[0]), float(_HEAD_DOM_V[1]),
        c_lo, c_hi,
        f_lo, f_hi,
        float(_HEAD_DOM_G[0]), float(_HEAD_DOM_G[1]),
    )


def session_prune_scoring_bundle(
    bundle: FgResponseFrontierScoringBundle,
    curves: StatCurves,
) -> FgResponseFrontierScoringBundle:
    """Session-box cone prune of a scoring bundle for ONE solve run (GA path only; persist/audit
    consumers load the full bundle). Re-runs the 16-corner dominance filter with corners at the
    session's realizable stat box: every dropped row is dominated at every cell this inventory can
    evaluate, so scoring winners are identical while the GPU score loop, uploads, and VRAM shrink
    to the session-relevant rows. The surviving compact pattern IDs/counts form the bundle's in-memory pool, which
    every later batch scores in place."""
    import dataclasses

    row_count = int(bundle.surface_row_count)
    if row_count <= 0:
        return bundle
    v_lo, v_hi, c_lo, c_hi, f_lo, f_hi, g_lo, g_hi = session_head_dominance_box(curves)
    pattern_ids, counts, pattern_words, pattern_coeffs = gather_surface_patterns(
        bundle.surface_rows, bundle.surface_patterns, ((0, row_count),)
    )
    head_len = min(int(bundle.total_notes), 100)
    keep = _numba_session_box_keep_mask(
        pattern_ids,
        pattern_words,
        counts,
        np.ascontiguousarray(bundle.frontier_offsets, dtype=np.int32),
        np.ascontiguousarray(bundle.frontier_lengths, dtype=np.int32),
        0,
        int(head_len),
        v_lo, v_hi, c_lo, c_hi, f_lo, f_hi, g_lo, g_hi,
    )
    keep = np.asarray(keep, dtype=bool)
    if tuple(keep.shape) != (int(row_count),):
        raise ValueError("session-box prune keep mask has the wrong shape")
    lengths_all = np.asarray(bundle.frontier_lengths, dtype=np.int64)
    offsets_all = np.asarray(bundle.frontier_offsets, dtype=np.int64)
    ends_all = offsets_all + lengths_all
    if bool(np.any(offsets_all < 0)) or bool(np.any(lengths_all < 0)) or bool(np.any(ends_all > row_count)):
        raise ValueError("session-box prune received a frontier outside the surface pool")
    kept_prefix = np.empty(int(row_count) + 1, dtype=np.int64)
    kept_prefix[0] = 0
    # Cast the mask straight into the prefix buffer and accumulate in place (no N-row int64 copy).
    kept_prefix[1:] = keep
    np.cumsum(kept_prefix[1:], out=kept_prefix[1:])
    kept_lengths = kept_prefix[ends_all] - kept_prefix[offsets_all]
    if bool(np.any((lengths_all > 0) & (kept_lengths <= 0))):
        raise ValueError("session-box prune emptied a frontier -- the greedy filter must keep at least one row")
    new_offsets = kept_prefix[offsets_all]
    if int(kept_prefix[-1]) > int(np.iinfo(np.int32).max):
        raise OverflowError("session-box prune compact surface pool exceeds int32 offsets")
    pruned_counts = np.ascontiguousarray(counts[keep], dtype=np.int32)
    # Compact-loader IDs follow the persisted lexicographic pattern order. Dense-ranking the
    # surviving IDs (the sorted np.unique set and inverse) therefore recreates exactly the dense
    # IDs/table the retired row re-intern produced.
    pruned_pattern_ids = np.ascontiguousarray(pattern_ids[keep], dtype=np.int32)
    used_pattern_ids = _dense_rank_pattern_ids_inplace(pruned_pattern_ids, int(pattern_words.shape[0]))
    pruned_pattern_words = np.ascontiguousarray(pattern_words[used_pattern_ids], dtype=np.uint32)
    pruned_pattern_coeffs = np.ascontiguousarray(pattern_coeffs[used_pattern_ids], dtype=np.int32)
    return dataclasses.replace(
        bundle,
        surface_pattern_ids=pruned_pattern_ids,
        surface_pattern_words=pruned_pattern_words,
        surface_counts=pruned_counts,
        surface_pattern_head_coeffs=pruned_pattern_coeffs,
        frontier_offsets=np.ascontiguousarray(new_offsets, dtype=np.int32),
        frontier_lengths=np.ascontiguousarray(kept_lengths, dtype=np.int32),
        surface_row_count=int(pruned_pattern_ids.shape[0]),
    )


def _build_response_frontier_cache_payload(
    song: TimedSong,
    curves: StatCurves,
    *,
    stat_keys: Iterable[tuple[int, int]],
) -> tuple[FgResponseFrontierCachePayload, str]:
    _assert_head_dominance_box_covers(curves)
    keys = normalize_fg_response_stat_keys(stat_keys)
    song_inputs, raw_fill_by_ff, non_fever_base_by_ff, real_time_by_ft = _response_axes(song, curves)
    frontier_by_key: dict[tuple[int, int], FgResponseFrontierResult] = {}
    frontier_by_geometry: dict[tuple[float, int, float, bool], FgResponseFrontierResult] = {}
    missing_by_geometry: dict[tuple[float, int, float, bool], tuple[float, int, float]] = {}
    source_counts: Counter[str] = Counter()
    for ft_stat, ff_stat in keys:
        raw_fill = float(raw_fill_by_ff[ff_stat])
        non_fever_base = int(non_fever_base_by_ff[ff_stat])
        real_fever_time = float(real_time_by_ft[ft_stat])
        geometry_key = (raw_fill, non_fever_base, real_fever_time, bool(song_inputs.use_forced_great_timing))
        frontier = frontier_by_geometry.get(geometry_key)
        source = "memory"
        if frontier is not None and not _frontier_is_complete(frontier):
            frontier = None
        if frontier is None:
            missing_by_geometry.setdefault(
                geometry_key,
                (float(raw_fill), int(non_fever_base), float(real_fever_time)),
            )
            source = "built"
        else:
            frontier_by_geometry[geometry_key] = frontier
        source_counts[source] += 1
    if missing_by_geometry:
        missing_items = tuple(missing_by_geometry.items())
        # ONE batch call per song build: the batch entry owns region-core-table admission and
        # reduction. Tables build serially; independent reductions overlap only when their combined
        # exact build-peak bounds fit the historical exhaustive one-table allocation, while every song-invariant
        # input -- chart arrays, prefix activation-hit tables, end-index tables for ALL unique
        # fever times, global geometry canonicalization, and right-sized stamp workspaces -- is
        # built exactly once per song.
        built_frontiers = build_force_greats_response_first_frontiers_gpu_batch(
            timestamps=song_inputs.timestamps,
            perfect_candidate_timestamps=song_inputs.perfect_candidates,
            great_candidate_timestamps=song_inputs.great_candidates,
            perfect_floor_timestamps=song_inputs.perfect_floor,
            great_floor_timestamps=song_inputs.great_floor,
            late_great_floor_timestamps=song_inputs.late_great_floor,
            exit_ceiling_timestamps=song_inputs.exit_ceiling,
            lanes=song_inputs.lanes,
            geometries=tuple(item[1] for item in missing_items),
            use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
        )
        if len(built_frontiers) != len(missing_items):
            raise ValueError("FG response frontier GPU batch returned the wrong number of frontiers")
        for (geometry_key, _geometry), frontier in zip(missing_items, built_frontiers, strict=True):
            if not _frontier_is_complete(frontier):
                raise ValueError("FG response frontier cache requires first-frontier surfaces")
            frontier_by_geometry[geometry_key] = frontier
    for ft_stat, ff_stat in keys:
        raw_fill = float(raw_fill_by_ff[ff_stat])
        non_fever_base = int(non_fever_base_by_ff[ff_stat])
        real_fever_time = float(real_time_by_ft[ft_stat])
        geometry_key = (raw_fill, non_fever_base, real_fever_time, bool(song_inputs.use_forced_great_timing))
        frontier = frontier_by_geometry.get(geometry_key)
        if frontier is None:
            raise ValueError(f"FG response frontier geometry was not built: {geometry_key!r}")
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
    song: TimedSong,
    curves: StatCurves,
    *,
    stat_keys: Iterable[tuple[int, int]],
) -> FrontierCacheInfo:
    """Whether a payload with `stat_keys` is cached, checked without loading one: a request payload in memory, or the
    song's bundle in memory or as a complete file."""
    keys = normalize_fg_response_stat_keys(stat_keys)
    payload_key = fg_response_frontier_payload_cache_key(song, curves, keys)
    bundle_key = fg_response_frontier_bundle_cache_key(song, curves)
    if _payload_memory.get(payload_key) is not None:
        return FrontierCacheInfo(payload_key, FG_RESPONSE_FRONTIER_CACHE.serving_path(payload_key), "memory")
    bundle = _payload_memory.get(bundle_key)
    if (bundle is not None and _payload_subset(bundle, keys) is not None) or _payload_disk_is_complete(
        bundle_key, keys
    ):
        return FrontierCacheInfo(payload_key, FG_RESPONSE_FRONTIER_CACHE.serving_path(bundle_key), "disk")
    return FrontierCacheInfo(payload_key, FG_RESPONSE_FRONTIER_CACHE.serving_path(payload_key), "missing")


def _stat_key_index_rows(keys: tuple[tuple[int, int], ...]) -> np.ndarray:
    return np.asarray(keys, dtype=np.intp).reshape((-1, 2))


def _scoring_bundle(cache_key: tuple, arrays: dict[str, np.ndarray]) -> FgResponseFrontierScoringBundle:
    """A bundle file's arrays (store.read_compatible_bundle) as a scoring bundle over every stat key it holds."""
    stat_key_rows = np.asarray(arrays["stat_keys"], dtype=np.int32).reshape((-1, 2))
    frontier_idx_by_stat = np.full((MAX_STAT + 1, MAX_STAT + 1), -1, dtype=np.int32)
    frontier_idx_by_stat[stat_key_rows[:, 0], stat_key_rows[:, 1]] = np.asarray(arrays["frontier_ids"], dtype=np.int32)
    total_notes = int(arrays["total_notes"].item())
    if int(arrays["first_surface_head_len"].item()) != min(total_notes, 100):
        raise ValueError("FG response frontier scoring bundle has invalid surface head coefficient metadata")
    surface_rows = arrays["surface_rows"]
    return FgResponseFrontierScoringBundle(
        cache_key=cache_key,
        frontier_idx_by_stat=frontier_idx_by_stat,
        raw_fill_by_ff=np.asarray(arrays["raw_fill_by_ff"], dtype=np.float64),
        non_fever_base_by_ff=np.asarray(arrays["non_fever_base_by_ff"], dtype=np.int32),
        real_time_by_ft=np.asarray(arrays["real_time_by_ft"], dtype=np.float64),
        frontier_meta=np.asarray(arrays["frontier_meta"], dtype=np.int32),
        surface_pattern_ids=np.empty((0,), dtype=np.int32),
        surface_pattern_words=np.empty((0, 8), dtype=np.uint32),
        surface_counts=np.empty((0, 3), dtype=np.int32),
        surface_pattern_head_coeffs=np.empty((0, 4), dtype=np.int32),
        frontier_offsets=np.asarray(arrays["first_offsets"], dtype=np.int32),
        frontier_lengths=np.asarray(arrays["first_counts"], dtype=np.int32),
        surface_row_count=int(surface_rows.shape[1]),
        total_notes=total_notes,
        long_notes=int(arrays["long_notes"].item()),
        use_forced_great_timing=bool(int(arrays["use_forced_great_timing"].item())),
        surface_rows=surface_rows,
        surface_patterns=arrays["surface_patterns"],
    )


def _missing_stat_keys(bundle: FgResponseFrontierScoringBundle, keys: tuple[tuple[int, int], ...]) -> list:
    """The requested keys the bundle does not hold, sorted (`keys` is sorted)."""
    requested = _stat_key_index_rows(keys)
    present = bundle.frontier_idx_by_stat[requested[:, 0], requested[:, 1]] >= 0
    return [keys[int(idx)] for idx in np.flatnonzero(~present)]


def load_response_frontier_scoring_bundle(
    song: TimedSong,
    curves: StatCurves,
    *,
    stat_keys: Iterable[tuple[int, int]],
) -> FgResponseFrontierScoringBundle:
    """The song's scoring bundle (its whole file: every stat key it holds, with its surface tables) covering
    `stat_keys`. A bundle held in memory that lacks some is read again: another process may have extended the file."""
    keys = normalize_fg_response_stat_keys(stat_keys)
    bundle_key = fg_response_frontier_bundle_cache_key(song, curves)
    cached = _scoring_bundle_memory.get(bundle_key)
    if cached is not None and not _missing_stat_keys(cached, keys):
        return cached
    arrays = read_compatible_bundle(bundle_key)
    if arrays is None:
        raise ValueError(
            "FG response frontier scoring bundle is missing. Startup cache prebuild must build "
            "the candidate-independent all-FT/FF bundle before runtime scoring."
        )
    scoring_bundle = _scoring_bundle(bundle_key, arrays)
    missing = _missing_stat_keys(scoring_bundle, keys)
    if missing:
        raise ValueError(
            "FG response frontier scoring bundle does not cover requested stat keys. "
            "Startup cache prebuild must build the candidate-independent all-FT/FF bundle before runtime scoring: "
            f"{missing[:5]!r}"
        )
    _scoring_bundle_memory.put(bundle_key, scoring_bundle)
    return scoring_bundle


def build_or_load_response_frontier_payload(
    song: TimedSong,
    curves: StatCurves,
    *,
    stat_keys: Iterable[tuple[int, int]],
) -> FrontierCacheLoad[FgResponseFrontierCachePayload]:
    started = time.perf_counter()
    keys = normalize_fg_response_stat_keys(stat_keys)
    cache_key = fg_response_frontier_payload_cache_key(song, curves, keys)
    bundle_key = fg_response_frontier_bundle_cache_key(song, curves)
    bundle_path = FG_RESPONSE_FRONTIER_CACHE.serving_path(bundle_key)
    payload = _payload_memory.get(cache_key)
    if payload is not None and _payload_subset(payload, keys) is not None:
        return FrontierCacheLoad(
            payload=payload,
            cache_key=cache_key,
            disk_path=bundle_path,
            cache_source="memory",
            elapsed_ms=float((time.perf_counter() - started) * 1000.0),
        )
    source = "disk"
    bundle = _payload_memory.get(bundle_key)
    if bundle is None:
        bundle = _load_payload(bundle_key)
    payload = _payload_subset(bundle, keys)
    if payload is None:
        # A partial bundle is extended with disk as the authoritative base, while one cross-process owner holds the
        # read-merge-publish transaction.
        with _response_bundle_build_slots:
            with _response_bundle_build_lock(bundle_key):
                # Never merge against the process-local payload cache here: another process may have published a
                # larger bundle while this process was waiting for the lock.
                bundle = _load_payload(bundle_key)
                payload = _payload_subset(bundle, keys)
                if payload is None:
                    update, source = _build_response_frontier_cache_payload(
                        song, curves, stat_keys=_payload_missing_or_incomplete_keys(bundle, keys)
                    )
                    bundle = _merge_payloads(bundle, update)
                    _save_payload(bundle_key, bundle)
                    _scoring_bundle_memory.pop(bundle_key)
                    payload = _payload_subset(bundle, keys)
                _payload_memory.put(bundle_key, bundle)
    _payload_memory.put(cache_key, payload)
    return FrontierCacheLoad(
        payload=payload,
        cache_key=cache_key,
        disk_path=FG_RESPONSE_FRONTIER_CACHE.serving_path(bundle_key),
        cache_source=source,
        elapsed_ms=float((time.perf_counter() - started) * 1000.0),
    )


def ensure_response_frontier_cache_for_song(
    song: TimedSong,
    curves: StatCurves,
    *,
    stat_keys: Iterable[tuple[int, int]] | None = None,
) -> tuple[str, float, Path]:
    """Make sure the song's bundle with `stat_keys` (default: every FT/FF key) is on disk; returns (cache source,
    build ms, bundle file).

    The candidate-independent bundle is keyed by the song's timing, so a chart-only (non-precise) song has its own
    bundle, distinct from the precise one. A hit costs a metadata probe: it skips build_or_load's per-row object
    materialization (seconds on heavy bundles), which no caller of this needs (scoring reads the bundle file itself).
    A miss builds the requested cells, publishes them, then releases the song's
    memory tiers: build_or_load pins the merged bundle and request payload (~1 GB of frontier rows on heavy charts)
    in the process-wide payload tier, and nothing here reads them; the bundle re-opens from disk where it is needed.
    """
    keys = tuple(stat_keys) if stat_keys is not None else all_response_stat_keys()
    cache_info = fg_response_frontier_payload_cache_info(song, curves, stat_keys=keys)
    if cache_info.cache_source in {"disk", "memory"}:
        return cache_info.cache_source, 0.0, cache_info.disk_path
    try:
        result = build_or_load_response_frontier_payload(song, curves, stat_keys=keys)
    finally:
        release_fg_response_song_memory(fg_response_frontier_bundle_cache_key(song, curves))
    return result.cache_source, result.elapsed_ms, result.disk_path
