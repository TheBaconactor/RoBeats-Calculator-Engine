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
from .response_build_gpu_numba import _HEAD_DOM_C, _HEAD_DOM_F
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
    load_first_surface_scoring_rows,
    reset_fg_response_frontier_payload_cache,
)
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
    "fg_response_frontier_bundle_cache_key",
    "fg_response_frontier_geometry_cache_key",
    "fg_response_frontier_payload_cache_info",
    "fg_response_frontier_payload_cache_key",
    "frontier_result_from_scoring_bundle",
    "frontier_result_from_scoring_bundle_for_stats",
    "all_response_stat_keys",
    "load_first_surface_scoring_rows",
    "load_response_frontier_scoring_bundle",
    "normalize_fg_response_stat_keys",
    "reset_fg_response_frontier_payload_cache",
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
        build_t0 = time.perf_counter()
        built_frontiers = build_force_greats_response_first_frontiers_gpu_batch(
            timestamps=song_inputs.timestamps,
            perfect_candidate_timestamps=song_inputs.perfect_candidates,
            great_candidate_timestamps=song_inputs.great_candidates,
            perfect_floor_timestamps=song_inputs.perfect_floor,
            great_floor_timestamps=song_inputs.great_floor,
            geometries=tuple(item[1] for item in missing_items),
            use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
        )
        frontier_build_ms = float((time.perf_counter() - build_t0) * 1000.0)
        emit_profile_event(
            component="fg_response_cache",
            event="frontier_build",
            metrics={
                "requested_stat_keys": int(len(keys)),
                "missing_geometries": int(len(missing_items)),
                "frontier_build_ms": frontier_build_ms,
                "total_notes": int(song_inputs.total_notes),
                "long_notes": int(song_inputs.long_notes),
            },
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
    surface_words = np.empty((0, 8), dtype=np.uint32)
    surface_counts = np.empty((0, 3), dtype=np.int32)
    surface_head_coeffs = np.empty((0, 4), dtype=np.int32)
    return FgResponseFrontierScoringBundle(
        cache_key=cache_key,
        frontier_idx_by_key=frontier_idx_by_key,
        frontier_idx_by_stat=frontier_idx_by_stat,
        raw_fill_by_ff=np.asarray(arrays["raw_fill_by_ff"], dtype=np.float64),
        non_fever_base_by_ff=np.asarray(arrays["non_fever_base_by_ff"], dtype=np.int32),
        real_time_by_ft=np.asarray(arrays["real_time_by_ft"], dtype=np.float64),
        frontier_meta=np.asarray(arrays["frontier_meta"], dtype=np.int32),
        surface_words=surface_words,
        surface_counts=surface_counts,
        surface_head_coeffs=surface_head_coeffs,
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
