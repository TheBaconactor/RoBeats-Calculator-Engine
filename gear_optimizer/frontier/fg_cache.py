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
    _dense_rank_pattern_ids_inplace,
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
from .producer_batch import build_first_frontiers
from .producer_kernels import _HEAD_DOM_C, _HEAD_DOM_F, _HEAD_DOM_G, _HEAD_DOM_V, _numba_session_box_keep_mask
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
            f"producer_kernels.py (the lossless head prune requires the box to be a superset)."
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
    evaluate, so scoring winners are identical while the score loop shrinks to the session-relevant rows."""
    pool = bundle.pool
    row_count = int(pool.pattern_ids.shape[0])
    if row_count <= 0:
        return bundle
    keep = _numba_session_box_keep_mask(
        (pool.pattern_ids, pool.pattern_words, pool.counts, pool.frontier_offsets, pool.frontier_lengths),
        0, min(int(bundle.total_notes), 100), session_head_dominance_box(curves),
    )
    keep = np.asarray(keep, dtype=bool)
    if tuple(keep.shape) != (row_count,):
        raise ValueError("session-box prune keep mask has the wrong shape")
    lengths_all = np.asarray(pool.frontier_lengths, dtype=np.int64)
    offsets_all = np.asarray(pool.frontier_offsets, dtype=np.int64)
    ends_all = offsets_all + lengths_all
    if bool(np.any(offsets_all < 0)) or bool(np.any(lengths_all < 0)) or bool(np.any(ends_all > row_count)):
        raise ValueError("session-box prune received a frontier outside the surface pool")
    kept_prefix = np.empty(row_count + 1, dtype=np.int64)
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
    # Dense-ranking the surviving pattern IDs keeps the persisted lexicographic pattern order.
    pruned_pattern_ids = np.ascontiguousarray(pool.pattern_ids[keep], dtype=np.int32)
    used_pattern_ids = _dense_rank_pattern_ids_inplace(pruned_pattern_ids, int(pool.pattern_words.shape[0]))
    return dataclasses.replace(
        bundle,
        pool=SurfacePool(
            frontier_offsets=np.ascontiguousarray(new_offsets, dtype=np.int32),
            frontier_lengths=np.ascontiguousarray(kept_lengths, dtype=np.int32),
            pattern_ids=pruned_pattern_ids,
            pattern_words=np.ascontiguousarray(pool.pattern_words[used_pattern_ids], dtype=np.uint32),
            counts=np.ascontiguousarray(pool.counts[keep], dtype=np.int32),
            head_coeffs=np.ascontiguousarray(pool.head_coeffs[used_pattern_ids], dtype=np.int32),
            head_greats=np.ascontiguousarray(pool.head_greats[used_pattern_ids], dtype=np.int32),
        ),
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
    built = build_first_frontiers(
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.great_floor,
        late_great_floor_timestamps=song_inputs.late_great_floor,
        exit_ceiling_timestamps=song_inputs.exit_ceiling,
        lanes=song_inputs.lanes,
        geometries=geometries,
        use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
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
        frontier_meta=np.asarray(arrays["frontier_meta"], dtype=np.int32),
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
