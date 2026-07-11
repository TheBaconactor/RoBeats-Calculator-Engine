from __future__ import annotations

import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs

from .response_build_gpu_batch import build_force_greats_response_first_frontiers_gpu_batch
from .response_build_gpu_numba import _HEAD_DOM_C, _HEAD_DOM_F, _HEAD_DOM_G, _HEAD_DOM_V, _numba_session_box_keep_mask
from .response_cache_keys import (
    _fg_response_disk_cache_dir,
    _fg_response_disk_cache_path,
    _response_axes,
    fg_response_frontier_bundle_cache_key,
    fg_response_frontier_geometry_cache_key,
    fg_response_frontier_payload_cache_key,
)
from .response_cache_serde import (
    frontier_result_from_scoring_bundle,
    frontier_result_from_scoring_bundle_for_stats,
)
from .response_cache_store import (
    _frontier_is_complete,
    _invalidate_bundle_array_views,
    _load_bundle_array_members,
    _load_payload,
    _memory_put,  # noqa: F401
    _payload_disk_info_if_complete,
    _payload_memory_get,
    _payload_memory_put,
    _response_bundle_build_slots,
    _save_payload,
    _scoring_bundle_memory_get,
    _scoring_bundle_memory_put,
    compress_cache_dir_sidecars,
    load_first_surface_scoring_patterns,
    load_first_surface_scoring_rows,
    purge_stale_version_cache_files,
    release_fg_response_song_memory,
    reset_fg_response_frontier_payload_cache,
    sweep_fg_response_frontier_live_cache,
)
from .response_cache_patterns import intern_surface_rows, unpack_surface_patterns
from .response_cache_types import (
    _FG_RESPONSE_CACHE_VERSION,
    _SCORING_BUNDLE_ARRAY_NAMES,
    FgResponseFrontierCacheInfo,
    FgResponseFrontierCachePayload,
    FgResponseFrontierPrewarmResult,
    FgResponseFrontierScoringBundle,
    _normalize_stat_key,
    all_response_stat_keys,
    normalize_fg_response_stat_keys,
)
from .response_types import FgResponseFrontierResult

__all__ = [
    "FgResponseFrontierCacheInfo",
    "FgResponseFrontierCachePayload",
    "FgResponseFrontierPrewarmResult",
    "FgResponseFrontierScoringBundle",
    "_FG_RESPONSE_CACHE_VERSION",
    "_fg_response_disk_cache_path",
    "build_or_load_response_frontier_payload",
    "cleanup_fg_response_frontier_cache_temp_files",
    "compress_cache_dir_sidecars",
    "fg_response_frontier_bundle_cache_key",
    "fg_response_frontier_geometry_cache_key",
    "fg_response_frontier_payload_cache_info",
    "fg_response_frontier_payload_cache_key",
    "frontier_result_from_scoring_bundle",
    "frontier_result_from_scoring_bundle_for_stats",
    "all_response_stat_keys",
    "load_first_surface_scoring_rows",
    "load_first_surface_scoring_patterns",
    "session_head_dominance_box",
    "session_prune_scoring_bundle",
    "load_response_frontier_scoring_bundle",
    "normalize_fg_response_stat_keys",
    "purge_stale_version_cache_files",
    "release_fg_response_song_memory",
    "reset_fg_response_frontier_payload_cache",
    "sweep_fg_response_frontier_live_cache",
]


def _source_label(counts: Counter[str]) -> str:
    if int(counts.get("built", 0)) > 0:
        return "built"
    active = [name for name in ("memory", "disk") if int(counts.get(name, 0)) > 0]
    if len(active) == 1:
        return active[0]
    return "mixed" if active else "missing"


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


def _assert_head_dominance_box_covers(ref_arrays: dict[str, Any]) -> None:
    """Fail loud if a gear rebalance pushes the combo/fever multipliers outside the lossless
    head-dominance box (_HEAD_DOM_C/_HEAD_DOM_F). The 16-corner prune is exact ONLY while the box is
    a superset of the realizable (c, f) cone, so a stale box must never silently under-cover.

    Axis-only refs (the cache unit tests pass just Fever Time / Fever Fill Rate) carry no gear
    (c, f) cone to validate -- the prune still uses the _HEAD_DOM_* box constants -- so there is
    nothing to check and the guard is a no-op."""
    cm_lut = ref_arrays.get("Combo Multiplier")
    fm_lut = ref_arrays.get("Fever Multiplier")
    if cm_lut is None or fm_lut is None:
        return
    cm = np.asarray(cm_lut, dtype=np.float64)
    fm = np.asarray(fm_lut, dtype=np.float64)
    if cm.size == 0 or fm.size == 0:
        return
    if not (_HEAD_DOM_C[0] <= float(cm.min()) and float(cm.max()) <= _HEAD_DOM_C[1]
            and _HEAD_DOM_F[0] <= float(fm.min()) and float(fm.max()) <= _HEAD_DOM_F[1]):
        raise ValueError(
            f"FG head-dominance box combo{_HEAD_DOM_C} fever{_HEAD_DOM_F} no longer covers the gear's "
            f"combo-mul [{float(cm.min()):.4f},{float(cm.max()):.4f}] / fever-mul "
            f"[{float(fm.min()):.4f},{float(fm.max()):.4f}] -- update _HEAD_DOM_C/_HEAD_DOM_F in "
            f"response_build_gpu_numba.py (the lossless head prune requires the box to be a superset)."
        )


def session_head_dominance_box(ref_arrays: dict[str, Any]) -> tuple[float, float, float, float, float, float, float, float]:
    """The SESSION's 16-corner dominance box: combo/fever corners tightened to the inventory's
    measured LUT ranges (the same arrays `_assert_head_dominance_box_covers` validates), value and
    great corners kept at the global box (v1: their per-note derivation is color-coupled; the
    global corners stay a sound cover). Fails loud without the LUTs -- the session prune is a
    GA-solve feature and the solve path always carries full reference arrays."""
    cm_lut = ref_arrays.get("Combo Multiplier")
    fm_lut = ref_arrays.get("Fever Multiplier")
    if cm_lut is None or fm_lut is None:
        raise ValueError("session dominance box requires Combo Multiplier / Fever Multiplier reference arrays")
    cm = np.asarray(cm_lut, dtype=np.float64)
    fm = np.asarray(fm_lut, dtype=np.float64)
    if cm.size == 0 or fm.size == 0:
        raise ValueError("session dominance box requires non-empty multiplier reference arrays")
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
    ref_arrays: dict[str, Any],
) -> FgResponseFrontierScoringBundle:
    """Session-box cone prune of a scoring bundle for ONE solve run (GA path only; persist/audit
    consumers load the full bundle). Re-runs the 16-corner dominance filter with corners at the
    session's realizable stat box: every dropped row is dominated at every cell this inventory can
    evaluate, so scoring winners are identical while the GPU score loop, uploads, and VRAM shrink
    to the session-relevant rows. Also materializes the surviving rows in memory, which subsumes
    the sidecar page-cache warm (no per-batch memmap gathers afterwards)."""
    import dataclasses

    row_count = int(bundle.surface_row_count)
    if row_count <= 0:
        return bundle
    v_lo, v_hi, c_lo, c_hi, f_lo, f_hi, g_lo, g_hi = session_head_dominance_box(ref_arrays)
    rows, coeff_rows = load_first_surface_scoring_rows(bundle.cache_key, ((0, row_count),))
    words = np.ascontiguousarray(rows[:, :8], dtype=np.uint32)
    counts = np.ascontiguousarray(rows[:, 8:11].astype(np.int32), dtype=np.int32)
    head_len = min(int(bundle.total_notes), 100)
    keep = _numba_session_box_keep_mask(
        words,
        counts,
        np.ascontiguousarray(bundle.frontier_offsets, dtype=np.int32),
        np.ascontiguousarray(bundle.frontier_lengths, dtype=np.int32),
        0,
        int(head_len),
        v_lo, v_hi, c_lo, c_hi, f_lo, f_hi, g_lo, g_hi,
    )
    keep = np.asarray(keep, dtype=bool)
    lengths_all = np.asarray(bundle.frontier_lengths, dtype=np.int64)
    offsets_all = np.asarray(bundle.frontier_offsets, dtype=np.int64)
    ends_all = offsets_all + lengths_all
    if bool(np.any(offsets_all < 0)) or bool(np.any(lengths_all < 0)) or bool(np.any(ends_all > row_count)):
        raise ValueError("session-box prune received a frontier outside the surface pool")
    kept_prefix = np.empty(int(row_count) + 1, dtype=np.int64)
    kept_prefix[0] = 0
    np.cumsum(np.asarray(keep, dtype=np.int64), out=kept_prefix[1:])
    kept_lengths = kept_prefix[ends_all] - kept_prefix[offsets_all]
    if bool(np.any((lengths_all > 0) & (kept_lengths <= 0))):
        raise ValueError("session-box prune emptied a frontier -- the greedy filter must keep at least one row")
    new_offsets = kept_prefix[offsets_all]
    if int(kept_prefix[-1]) > int(np.iinfo(np.int32).max):
        raise OverflowError("session-box prune compact surface pool exceeds int32 offsets")
    pruned_words = np.ascontiguousarray(words[keep], dtype=np.uint32)
    pruned_counts = np.ascontiguousarray(counts[keep], dtype=np.int32)
    pruned_coeffs = np.ascontiguousarray(coeff_rows[keep].astype(np.int32), dtype=np.int32)
    pruned_rows = np.empty((int(pruned_words.shape[0]), 11), dtype=np.uint32)
    pruned_rows[:, :8] = pruned_words
    pruned_rows[:, 8:11] = np.asarray(pruned_counts, dtype=np.uint32)
    row_refs, patterns = intern_surface_rows(pruned_rows, pruned_coeffs)
    pattern_words, pattern_coeffs = unpack_surface_patterns(patterns)
    return dataclasses.replace(
        bundle,
        surface_pattern_ids=np.ascontiguousarray(row_refs[:, 0], dtype=np.int32),
        surface_pattern_words=pattern_words,
        surface_counts=np.ascontiguousarray(row_refs[:, 1:4], dtype=np.int32),
        surface_pattern_head_coeffs=pattern_coeffs,
        frontier_offsets=np.ascontiguousarray(new_offsets, dtype=np.int32),
        frontier_lengths=np.ascontiguousarray(kept_lengths, dtype=np.int32),
        surface_row_count=int(row_refs.shape[0]),
    )


def _build_response_frontier_cache_payload(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    stat_keys: Iterable[tuple[int, int]],
) -> tuple[FgResponseFrontierCachePayload, str]:
    _assert_head_dominance_box_covers(ref_arrays)
    keys = normalize_fg_response_stat_keys(stat_keys)
    song_inputs, raw_fill_by_ff, non_fever_base_by_ff, real_time_by_ft = _response_axes(calc_song, ref_arrays)
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
        batch_stats: dict[str, Any] = {}
        build_t0 = time.perf_counter()
        built_frontiers = build_force_greats_response_first_frontiers_gpu_batch(
            timestamps=song_inputs.timestamps,
            perfect_candidate_timestamps=song_inputs.perfect_candidates,
            great_candidate_timestamps=song_inputs.great_candidates,
            perfect_floor_timestamps=song_inputs.perfect_floor,
            great_floor_timestamps=song_inputs.great_floor,
            lanes=song_inputs.lanes,
            geometries=tuple(item[1] for item in missing_items),
            use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
            stats_sink=batch_stats,
        )
        batch_entry_invocations = 1
        if len(built_frontiers) != len(missing_items):
            raise ValueError("FG response frontier GPU batch returned the wrong number of frontiers")
        for (geometry_key, _geometry), frontier in zip(missing_items, built_frontiers, strict=True):
            if not _frontier_is_complete(frontier):
                raise ValueError("FG response frontier cache requires first-frontier surfaces")
            frontier_by_geometry[geometry_key] = frontier
        frontier_build_ms = float((time.perf_counter() - build_t0) * 1000.0)
        emit_profile_event(
            component="fg_response_cache",
            event="frontier_build",
            metrics={
                "requested_stat_keys": int(len(keys)),
                "missing_geometries": int(len(missing_items)),
                "batch_entry_invocations": int(batch_entry_invocations),
                "frontier_build_ms": frontier_build_ms,
                "total_notes": int(song_inputs.total_notes),
                "long_notes": int(song_inputs.long_notes),
                **{str(key): value for key, value in batch_stats.items()},
            },
        )
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
    disk_info = _payload_disk_info_if_complete(payload_key, keys)
    if disk_info is not None:
        total_notes, long_notes, frontier_count = disk_info
        return FgResponseFrontierCacheInfo(
            cache_key=payload_key,
            disk_path=_fg_response_disk_cache_path(payload_key),
            cache_source="disk",
            total_notes=int(total_notes),
            long_notes=int(long_notes),
            frontier_count=int(frontier_count),
        )
    bundle = _payload_memory_get(bundle_key)
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
    bundle_disk_info = _payload_disk_info_if_complete(bundle_key, keys)
    if bundle_disk_info is not None:
        total_notes, long_notes, frontier_count = bundle_disk_info
        return FgResponseFrontierCacheInfo(
            cache_key=payload_key,
            disk_path=_fg_response_disk_cache_path(bundle_key),
            cache_source="disk",
            total_notes=int(total_notes),
            long_notes=int(long_notes),
            frontier_count=int(frontier_count),
        )
    song_inputs = extract_fg_song_inputs(calc_song)
    return FgResponseFrontierCacheInfo(
        cache_key=payload_key,
        disk_path=_fg_response_disk_cache_path(payload_key),
        cache_source="missing",
        total_notes=int(song_inputs.total_notes),
        long_notes=int(song_inputs.long_notes),
        frontier_count=0,
    )


def _materialize_scoring_bundle_from_arrays(
    *,
    cache_key: tuple,
    keys: tuple[tuple[int, int], ...],
    arrays: dict[str, np.ndarray],
) -> FgResponseFrontierScoringBundle:
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
    total_notes = int(np.asarray(arrays["total_notes"]).item())
    expected_head_len = min(int(total_notes), 100)
    persisted_head_len = arrays.get("first_surface_head_len")
    if persisted_head_len is None or int(np.asarray(persisted_head_len).item()) != int(expected_head_len):
        raise ValueError("FG response frontier scoring bundle has invalid surface head coefficient metadata")
    surface_pattern_ids = np.empty((0,), dtype=np.int32)
    surface_pattern_words = np.empty((0, 8), dtype=np.uint32)
    surface_counts = np.empty((0, 3), dtype=np.int32)
    surface_pattern_head_coeffs = np.empty((0, 4), dtype=np.int32)
    return FgResponseFrontierScoringBundle(
        cache_key=cache_key,
        frontier_idx_by_key=frontier_idx_by_key,
        frontier_idx_by_stat=frontier_idx_by_stat,
        raw_fill_by_ff=np.asarray(arrays["raw_fill_by_ff"], dtype=np.float64),
        non_fever_base_by_ff=np.asarray(arrays["non_fever_base_by_ff"], dtype=np.int32),
        real_time_by_ft=np.asarray(arrays["real_time_by_ft"], dtype=np.float64),
        frontier_meta=np.asarray(arrays["frontier_meta"], dtype=np.int32),
        surface_pattern_ids=surface_pattern_ids,
        surface_pattern_words=surface_pattern_words,
        surface_counts=surface_counts,
        surface_pattern_head_coeffs=surface_pattern_head_coeffs,
        frontier_offsets=np.asarray(arrays["first_offsets"], dtype=np.int32),
        frontier_lengths=np.asarray(arrays["first_counts"], dtype=np.int32),
        surface_row_count=int(np.asarray(arrays["first_surface_row_count"]).item()),
        total_notes=int(total_notes),
        long_notes=int(np.asarray(arrays["long_notes"]).item()),
        use_forced_great_timing=bool(int(np.asarray(arrays["use_forced_great_timing"]).item())),
    )


def load_response_frontier_scoring_bundle(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    stat_keys: Iterable[tuple[int, int]],
) -> FgResponseFrontierScoringBundle:
    keys = normalize_fg_response_stat_keys(stat_keys)
    bundle_key = fg_response_frontier_bundle_cache_key(calc_song, ref_arrays)
    cached_scoring = _scoring_bundle_memory_get(bundle_key)
    if cached_scoring is not None:
        if len(cached_scoring.frontier_idx_by_key) >= (TOTAL_ROWS + 1) * (TOTAL_ROWS + 1) or all(
            key in cached_scoring.frontier_idx_by_key for key in keys
        ):
            return cached_scoring

    try:
        arrays = _load_bundle_array_members(bundle_key, names=_SCORING_BUNDLE_ARRAY_NAMES)
    except ValueError as exc:
        raise ValueError(
            "FG response frontier scoring bundle is missing. Startup cache prebuild must build "
            "the candidate-independent all-FT/FF bundle before runtime scoring."
        ) from exc
    present = {
        _normalize_stat_key((int(row[0]), int(row[1])))
        for row in np.asarray(arrays.get("stat_keys", ()), dtype=np.int32).reshape((-1, 2))
    }
    if not set(keys).issubset(present):
        missing = sorted(set(keys) - present)
        raise ValueError(
            "FG response frontier scoring bundle does not cover requested stat keys. "
            "Startup cache prebuild must build the candidate-independent all-FT/FF bundle before runtime scoring: "
            f"{missing[:5]!r}"
        )
    scoring_bundle = _materialize_scoring_bundle_from_arrays(cache_key=bundle_key, keys=keys, arrays=arrays)
    _scoring_bundle_memory_put(bundle_key, scoring_bundle)
    return scoring_bundle

def build_or_load_response_frontier_payload(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    stat_keys: Iterable[tuple[int, int]],
) -> FgResponseFrontierPrewarmResult:
    started = time.perf_counter()
    keys = normalize_fg_response_stat_keys(stat_keys)
    cache_key = fg_response_frontier_payload_cache_key(calc_song, ref_arrays, keys)
    bundle_key = fg_response_frontier_bundle_cache_key(calc_song, ref_arrays)
    bundle_path = _fg_response_disk_cache_path(bundle_key)
    payload = _payload_memory_get(cache_key)
    if payload is not None and _payload_subset(payload, keys) is not None:
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
    payload = _load_payload(cache_key)
    if _payload_subset(payload, keys) is None:
        payload = None
    bundle: FgResponseFrontierCachePayload | None = None
    if payload is None:
        slot_wait_t0 = time.perf_counter()
        with _response_bundle_build_slots:
            bundle_slot_wait_ms = float((time.perf_counter() - slot_wait_t0) * 1000.0)
            bundle = _payload_memory_get(bundle_key)
            if bundle is None:
                bundle = _load_payload(bundle_key)
            if bundle is not None:
                payload = _payload_subset(bundle, keys)
            if payload is None:
                missing_keys = _payload_missing_or_incomplete_keys(bundle, keys)
                build_t0 = time.perf_counter()
                payload, source = _build_response_frontier_cache_payload(
                    calc_song,
                    ref_arrays,
                    stat_keys=missing_keys,
                )
                build_ms = float((time.perf_counter() - build_t0) * 1000.0)
                save_t0 = time.perf_counter()
                bundle = _merge_payloads(bundle, payload)
                _save_payload(bundle_key, bundle)
                save_ms = float((time.perf_counter() - save_t0) * 1000.0)
                _payload_memory_put(bundle_key, bundle)
                _invalidate_bundle_array_views(bundle_key)
                payload = _payload_subset(bundle, keys)
                emit_profile_event(
                    component="fg_response_cache",
                    event="payload_materialize",
                    metrics={
                        "requested_stat_keys": int(len(keys)),
                        "missing_stat_keys": int(len(missing_keys)),
                        "payload_build_ms": build_ms,
                        "bundle_save_ms": save_ms,
                        "bundle_slot_wait_ms": bundle_slot_wait_ms,
                        "bundle_stat_keys": int(len(bundle.frontier_by_key)),
                    },
                )
                if payload is None:
                    raise ValueError("FG response frontier bundle did not contain requested keys after build")
            else:
                source = "disk"
    else:
        bundle = _merge_payloads(_load_payload(bundle_key), payload)
        _save_payload(bundle_key, bundle)
        _payload_memory_put(bundle_key, bundle)
        _invalidate_bundle_array_views(bundle_key)
    _payload_memory_put(cache_key, payload)
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
