from __future__ import annotations

from dataclasses import dataclass, replace
import time
from typing import Any

import numpy as np

from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.constants import (
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    TOTAL_GEM_BUDGET,
    TOTAL_ROWS,
)
from gear_optimizer.core.gem_defs import build_gem_counts
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats

from .response_builder import reconstruct_force_greats_response_counts, reconstruct_force_greats_response_trace
from .response_cache import (
    FgResponseFrontierScoringBundle,
    all_response_stat_keys,
    frontier_result_from_scoring_bundle_for_stats,
    load_first_surface_scoring_rows,
    load_response_frontier_scoring_bundle,
)
from .response_ftff_prune import element_ftff_delta
from .response_inner_host import _score_response_group_meta_gpu
from .response_types import (
    FgResponseFrontierResult,
    FgResponseFrontierSolveResult,
    FgResponseInnerResult,
    FgResponseSurface,
)

__all__ = [
    "FgResponseFrontierResult",
    "FgResponseFrontierSolveResult",
    "FgResponseInnerResult",
    "FgResponseSurface",
    "FgResponseFrontierPackedScoringBatch",
    "FgResponseFrontierOwnerResult",
    "prepare_force_greats_response_frontier_scoring_batch",
    "build_prepared_force_greats_response_frontier_group_arrays_on_owner",
    "score_prepared_force_greats_response_frontier_batch_on_gpu_owner",
    "score_prepared_force_greats_response_frontier_batch_sync",
    "materialize_force_greats_response_frontier_owner_result",
    "run_prepared_force_greats_response_frontier_batches_via_client",
    "reconstruct_force_greats_response_counts",
    "reconstruct_force_greats_response_trace",
]

_ResponsePair = tuple[int, int, FgResponseFrontierResult, float, float]


@dataclass(frozen=True, slots=True)
class FgResponseFrontierPackedScoringBatch:
    started: float
    stats_inputs: tuple[dict[str, Any], ...]
    calc_song: dict[str, Any]
    song_inputs: Any
    ref_arrays: dict[str, Any]
    selected_color: str
    primary_color: str
    secondary_color: str
    scoring_bundle: FgResponseFrontierScoringBundle
    scoring_bundle_ms: float
    # Host-side prep inputs; group rows and scoring surfaces are built on the GPU owner thread.
    base_components: np.ndarray
    ft_values: np.ndarray
    ff_values: np.ndarray
    residual_values: np.ndarray
    frontier_idx_by_stat: np.ndarray
    primary_ftff_delta_values: np.ndarray
    secondary_ftff_delta_values: np.ndarray
    score_elements_constant: bool
    head_len: int
    body_total: int
    group_meta: np.ndarray | None = None
    group_ft: np.ndarray | None = None
    group_ff: np.ndarray | None = None
    group_ft_stat: np.ndarray | None = None
    group_ff_stat: np.ndarray | None = None
    candidate_slices: tuple[tuple[int, int], ...] = ()
    kept_stat_keys: tuple[tuple[int, int], ...] = ()
    scoring_surface_words: np.ndarray | None = None
    scoring_surface_counts: np.ndarray | None = None
    scoring_surface_head_coeffs: np.ndarray | None = None
    scoring_group_offsets: np.ndarray | None = None
    scoring_group_lengths: np.ndarray | None = None
    scoring_unique_frontiers: int = 0
    scoring_surface_compact_ms: float = 0.0
    scoring_surface_head_coeff_ms: float = 0.0
    scoring_setup_ms: float = 0.0
    scoring_group_build_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class FgResponseFrontierOwnerResult:
    batch: FgResponseFrontierPackedScoringBatch
    inner_rows: np.ndarray


def _stats_after_ftff_for_inner(
    base_stats: dict[str, Any],
    *,
    ft: int,
    ff: int,
    primary_color: str,
    secondary_color: str,
) -> dict[str, int]:
    primary = str(primary_color or "")
    secondary = str(secondary_color or "")
    out = {
        "Perfect Points": int(base_stats.get("Perfect Points", 0) or 0),
        "Combo Multiplier": int(base_stats.get("Combo Multiplier", 0) or 0),
        "Fever Multiplier": int(base_stats.get("Fever Multiplier", 0) or 0),
        "Fever Time": int(base_stats.get("Fever Time", 0) or 0) + int(ft) * GEM_SCALE_FEVER,
        "Fever Fill Rate": int(base_stats.get("Fever Fill Rate", 0) or 0) + int(ff) * GEM_SCALE_FEVER,
    }
    if primary:
        out[primary] = int(base_stats.get(primary, 0) or 0) + element_ftff_delta(primary, int(ft), int(ff))
    if secondary:
        out[secondary] = int(base_stats.get(secondary, 0) or 0) + element_ftff_delta(secondary, int(ft), int(ff))
    return out


def _surface_from_packed_arrays(
    *,
    surface_words: np.ndarray,
    surface_counts: np.ndarray,
    surface_idx: int,
) -> FgResponseSurface:
    idx = int(surface_idx)
    if idx < 0 or idx >= int(surface_words.shape[0]) or idx >= int(surface_counts.shape[0]):
        raise ValueError("response frontier exact GPU selected surface is outside the packed pool")
    word_row = np.asarray(surface_words[idx], dtype=np.uint32)
    count_row = np.asarray(surface_counts[idx], dtype=np.int32)
    return FgResponseSurface(
        int(word_row[0]),
        int(word_row[1]),
        int(word_row[2]),
        int(word_row[3]),
        int(word_row[4]),
        int(word_row[5]),
        int(word_row[6]),
        int(word_row[7]),
        int(count_row[0]),
        int(count_row[1]),
        int(count_row[2]),
    )


def _pack_scoring_surfaces_for_batch(
    *,
    scoring_bundle: FgResponseFrontierScoringBundle,
    group_meta: np.ndarray,
    group_ft_stat: np.ndarray,
    group_ff_stat: np.ndarray,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    int,
    float,
    float,
]:
    phase_t0 = time.perf_counter()
    kept_frontiers = np.ascontiguousarray(
        scoring_bundle.frontier_idx_by_stat[group_ft_stat, group_ff_stat],
        dtype=np.int32,
    )
    frontier_count = int(scoring_bundle.frontier_lengths.shape[0])
    if bool(np.any((kept_frontiers < 0) | (kept_frontiers >= frontier_count))):
        raise ValueError("FG response frontier stat key was not loaded for packed batch solve")

    frontier_lengths_all = np.asarray(scoring_bundle.frontier_lengths, dtype=np.int32)
    frontier_offsets_all = np.asarray(scoring_bundle.frontier_offsets, dtype=np.int32)
    if bool(np.any(frontier_lengths_all[kept_frontiers] <= 0)):
        raise ValueError("FG response frontier payload contains an empty first frontier")

    group_lengths = np.ascontiguousarray(frontier_lengths_all[kept_frontiers], dtype=np.int32)
    if bool(np.any(group_lengths <= 0)):
        raise ValueError("FG response frontier payload contains an empty first frontier")
    head_lengths = np.unique(np.ascontiguousarray(group_meta[:, 6], dtype=np.int32))
    if int(head_lengths.shape[0]) != 1:
        raise ValueError("response frontier GPU group metadata has inconsistent head length")
    unique_frontiers = np.ascontiguousarray(np.unique(kept_frontiers), dtype=np.int32)
    selected_segments = sorted(
        {
            (int(frontier_offsets_all[int(frontier_idx)]), int(frontier_lengths_all[int(frontier_idx)]))
            for frontier_idx in unique_frontiers
        }
    )
    copy_ranges: list[tuple[int, int, int]] = []
    segment_offsets: dict[tuple[int, int], int] = {}
    cursor = 0
    for start, length in selected_segments:
        if copy_ranges and int(copy_ranges[-1][0]) + int(copy_ranges[-1][1]) == int(start):
            prev_start, prev_length, target_start = copy_ranges[-1]
            copy_ranges[-1] = (int(prev_start), int(prev_length) + int(length), int(target_start))
            segment_offsets[(int(start), int(length))] = int(cursor)
        else:
            copy_ranges.append((int(start), int(length), int(cursor)))
            segment_offsets[(int(start), int(length))] = int(cursor)
        cursor += int(length)
    ranges = tuple((int(start), int(length)) for start, length, _target_start in copy_ranges)
    frontier_remap = np.full((frontier_count,), -1, dtype=np.int32)
    for frontier_idx in unique_frontiers:
        segment = (
            int(frontier_offsets_all[int(frontier_idx)]),
            int(frontier_lengths_all[int(frontier_idx)]),
        )
        frontier_remap[int(frontier_idx)] = int(segment_offsets[segment])
    group_offsets = np.ascontiguousarray(frontier_remap[kept_frontiers], dtype=np.int32)
    if bool(np.any(group_offsets < 0)):
        raise ValueError("FG response frontier packed batch failed to remap selected frontiers")

    full_surface_words = np.asarray(scoring_bundle.surface_words)
    full_surface_counts = np.asarray(scoring_bundle.surface_counts)
    full_surface_head_coeffs = np.asarray(scoring_bundle.surface_head_coeffs)
    if int(full_surface_words.shape[0]) > 0:
        if (
            int(full_surface_words.ndim) != 2
            or int(full_surface_words.shape[1]) != 8
            or int(full_surface_counts.ndim) != 2
            or int(full_surface_counts.shape[0]) != int(full_surface_words.shape[0])
            or int(full_surface_counts.shape[1]) != 3
            or int(full_surface_head_coeffs.ndim) != 2
            or int(full_surface_head_coeffs.shape[0]) != int(full_surface_words.shape[0])
            or int(full_surface_head_coeffs.shape[1]) != 4
        ):
            raise ValueError("FG response frontier scoring bundle has invalid in-memory surface arrays")
        surface_words = np.empty((int(cursor), 8), dtype=np.uint32)
        surface_counts = np.empty((int(cursor), 3), dtype=np.int32)
        surface_head_coeffs = np.empty((int(cursor), 4), dtype=np.int32)
        for source_start, length, compact_start in copy_ranges:
            source_end = int(source_start) + int(length)
            target_start = int(compact_start)
            target_end = target_start + int(length)
            surface_words[target_start:target_end] = full_surface_words[int(source_start) : source_end]
            surface_counts[target_start:target_end] = full_surface_counts[int(source_start) : source_end]
            surface_head_coeffs[target_start:target_end] = full_surface_head_coeffs[int(source_start) : source_end]
    else:
        surface_rows, surface_head_coeffs = load_first_surface_scoring_rows(scoring_bundle.cache_key, ranges)
        surface_words = np.ascontiguousarray(surface_rows[:, :8], dtype=np.uint32)
        surface_counts = np.ascontiguousarray(surface_rows[:, 8:11], dtype=np.int32)
        surface_head_coeffs = np.ascontiguousarray(surface_head_coeffs, dtype=np.int32)
    compact_ms = float((time.perf_counter() - phase_t0) * 1000.0)
    head_coeff_ms = 0.0
    if (
        int(surface_head_coeffs.ndim) != 2
        or int(surface_head_coeffs.shape[0]) != int(surface_words.shape[0])
        or int(surface_head_coeffs.shape[1]) != 4
    ):
        raise ValueError("FG response frontier scoring bundle has invalid surface head coefficients")
    return (
        np.ascontiguousarray(surface_words, dtype=np.uint32),
        np.ascontiguousarray(surface_counts, dtype=np.int32),
        surface_head_coeffs,
        group_offsets,
        group_lengths,
        int(unique_frontiers.shape[0]),
        compact_ms,
        head_coeff_ms,
    )


def _unique_response_stat_keys_tuple(
    *,
    group_ft_stat: np.ndarray,
    group_ff_stat: np.ndarray,
    frontier_idx_by_stat: np.ndarray,
) -> tuple[tuple[int, int], ...]:
    axis = int(TOTAL_ROWS) + 1
    encoded = np.ascontiguousarray(
        (np.asarray(group_ft_stat, dtype=np.int32) * axis) + np.asarray(group_ff_stat, dtype=np.int32),
        dtype=np.int32,
    )
    unique_encoded = np.unique(encoded)
    unique_ft = np.asarray(unique_encoded // axis, dtype=np.int32)
    unique_ff = np.asarray(unique_encoded - (unique_ft * axis), dtype=np.int32)
    if bool(np.any(frontier_idx_by_stat[unique_ft, unique_ff] < 0)):
        raise ValueError("FG response frontier prewarmed scoring bundle does not cover requested stat keys")
    return tuple(zip((int(v) for v in unique_ft), (int(v) for v in unique_ff), strict=True))


_GROUP_ROW_BUILDER_WARMED = False


def warmup_response_frontier_group_builder() -> None:
    global _GROUP_ROW_BUILDER_WARMED
    if bool(_GROUP_ROW_BUILDER_WARMED):
        return
    from .response_group_build_kernels import build_response_group_rows_gpu

    ft_values, ff_values, residual_values = ftff_combo_arrays(2)
    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    for pos in range(int(ft_values.shape[0])):
        ft_stat = min(TOTAL_ROWS, int(ft_values[pos]) * GEM_SCALE_FEVER)
        ff_stat = min(TOTAL_ROWS, int(ff_values[pos]) * GEM_SCALE_FEVER)
        frontier_idx_by_stat[ft_stat, ff_stat] = int(pos)
    base_components = np.asarray([[0, 0, 0, 1, 2, 0, 0]], dtype=np.int32)
    primary_delta = np.asarray(ft_values * GEM_STAT_TO_ELEMENT_SCALE, dtype=np.int32)
    secondary_delta = np.asarray(ff_values * GEM_STAT_TO_ELEMENT_SCALE, dtype=np.int32)
    group_meta, group_ft, group_ff, group_ft_stat, group_ff_stat, candidate_slices = build_response_group_rows_gpu(
        np.ascontiguousarray(base_components, dtype=np.int32),
        np.ascontiguousarray(ft_values, dtype=np.int32),
        np.ascontiguousarray(ff_values, dtype=np.int32),
        np.ascontiguousarray(residual_values, dtype=np.int32),
        np.ascontiguousarray(frontier_idx_by_stat, dtype=np.int32),
        np.ascontiguousarray(primary_delta, dtype=np.int32),
        np.ascontiguousarray(secondary_delta, dtype=np.int32),
        False,
        1,
        0,
    )
    if (
        int(group_meta.shape[0]) != int(ft_values.shape[0])
        or group_ft.tolist() != ft_values.astype(np.int32, copy=False).tolist()
        or group_ff.tolist() != ff_values.astype(np.int32, copy=False).tolist()
        or group_ft_stat.tolist() != (ft_values * GEM_SCALE_FEVER).astype(np.int32, copy=False).tolist()
        or group_ff_stat.tolist() != (ff_values * GEM_SCALE_FEVER).astype(np.int32, copy=False).tolist()
        or candidate_slices.tolist() != [[0, int(ft_values.shape[0])]]
    ):
        raise RuntimeError("FG response group-row builder warmup produced an invalid result")
    _GROUP_ROW_BUILDER_WARMED = True


def _solve_result_from_row(
    *,
    started: float,
    base_stats: dict[str, Any],
    selected_color: str,
    song_inputs: Any,
    pair: _ResponsePair,
    row: tuple[int, int, int, int, int, int, int, int, int, int, int],
    surface: FgResponseSurface | None = None,
    include_forced_counts: bool = True,
) -> FgResponseFrontierSolveResult:
    ft, ff, frontier, raw_fill, real_fever_time = pair
    inner = FgResponseInnerResult(
        best_score=int(row[0]),
        surface_index=int(row[1]),
        g_pp=int(row[2]),
        g_cm=int(row[3]),
        g_fm=int(row[4]),
        g_ov=int(row[5]),
        final_pp=int(row[6]),
        final_cm=int(row[7]),
        final_fm=int(row[8]),
        final_primary=int(row[9]),
        final_secondary=int(row[10]),
    )
    surface = surface if surface is not None else frontier.first_frontier[int(inner.surface_index)]
    if include_forced_counts:
        forced_counts = reconstruct_force_greats_response_counts(
            frontier=frontier,
            target_surface=surface,
            timestamps=song_inputs.timestamps,
            perfect_candidate_timestamps=song_inputs.perfect_candidates,
            great_candidate_timestamps=song_inputs.great_candidates,
            raw_fever_fill=float(raw_fill),
            real_fever_time=float(real_fever_time),
            use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
        )
    else:
        forced_counts = ()
    final_stats = apply_gems_to_base_stats(
        base_stats,
        selected_color,
        int(ft),
        int(ff),
        int(inner.g_pp),
        int(inner.g_cm),
        int(inner.g_fm),
        int(inner.g_ov),
    )
    return FgResponseFrontierSolveResult(
        best_score=int(inner.best_score),
        ft=int(ft),
        ff=int(ff),
        gem_counts=build_gem_counts(int(inner.g_pp), int(inner.g_cm), int(inner.g_fm), int(inner.g_ov)),
        stats=final_stats,
        surface=surface,
        frontier=frontier,
        inner=inner,
        seconds=float(time.perf_counter() - started),
        forced_counts=tuple(int(v) for v in forced_counts),
        raw_fever_fill=float(raw_fill),
        real_fever_time=float(real_fever_time),
    )


def prepare_force_greats_response_frontier_scoring_batch(
    *,
    base_stats_list: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_color: str,
    total_budget: int = TOTAL_GEM_BUDGET,
    started: float | None = None,
    scoring_bundle: FgResponseFrontierScoringBundle | None = None,
) -> FgResponseFrontierPackedScoringBatch:
    """Prepare the GA->FG candidate inputs (host, prep thread). The group rows + scoring
    surfaces are built later on the GPU owner thread by
    `score_prepared_force_greats_response_frontier_batch_on_gpu_owner`."""
    setup_t0 = time.perf_counter()
    stats_inputs = tuple(dict(stats) for stats in (base_stats_list or []))
    if not stats_inputs:
        raise ValueError("response frontier exact scoring batch requires at least one candidate")

    ft_values, ff_values, remaining = ftff_combo_arrays(int(total_budget))
    if int(ft_values.shape[0]) <= 0:
        raise ValueError("response frontier exact solve found no FT/FF pairs")

    residual_values = np.asarray(remaining, dtype=np.int32)
    song_inputs = extract_fg_song_inputs(calc_song)
    primary_color = str(song_inputs.primary_color or "")
    secondary_color = str(song_inputs.secondary_color or "")
    primary_ft_delta = GEM_STAT_TO_ELEMENT_SCALE if primary_color == "Beat" else 0
    primary_ff_delta = GEM_STAT_TO_ELEMENT_SCALE if primary_color == "Vibe" else 0
    secondary_ft_delta = GEM_STAT_TO_ELEMENT_SCALE if secondary_color == "Beat" else 0
    secondary_ff_delta = GEM_STAT_TO_ELEMENT_SCALE if secondary_color == "Vibe" else 0
    score_elements_constant = (
        primary_ft_delta == 0
        and primary_ff_delta == 0
        and secondary_ft_delta == 0
        and secondary_ff_delta == 0
    )
    base_components = np.ascontiguousarray(
        np.asarray(
            [
                (
                    int(base_stats.get("Perfect Points", 0) or 0),
                    int(base_stats.get("Combo Multiplier", 0) or 0),
                    int(base_stats.get("Fever Multiplier", 0) or 0),
                    int(base_stats.get(primary_color, 0) or 0) if primary_color else 0,
                    int(base_stats.get(secondary_color, 0) or 0) if secondary_color else 0,
                    int(base_stats.get("Fever Time", 0) or 0),
                    int(base_stats.get("Fever Fill Rate", 0) or 0),
                )
                for base_stats in stats_inputs
            ],
            dtype=np.int32,
        )
    )
    bundle_t0 = time.perf_counter()
    if scoring_bundle is None:
        scoring_bundle = load_response_frontier_scoring_bundle(
            calc_song,
            ref_arrays,
            stat_keys=all_response_stat_keys(),
        )
    scoring_bundle_ms = float((time.perf_counter() - bundle_t0) * 1000.0)

    head_len = min(int(song_inputs.total_notes), 100)
    body_total = max(0, int(song_inputs.total_notes) - 100)
    frontier_idx_by_stat = np.ascontiguousarray(scoring_bundle.frontier_idx_by_stat, dtype=np.int32)
    primary_ftff_delta_values = np.asarray(
        (ft_values * int(primary_ft_delta)) + (ff_values * int(primary_ff_delta)),
        dtype=np.int32,
    )
    secondary_ftff_delta_values = np.asarray(
        (ft_values * int(secondary_ft_delta)) + (ff_values * int(secondary_ff_delta)),
        dtype=np.int32,
    )
    setup_ms = float((time.perf_counter() - setup_t0) * 1000.0)
    return FgResponseFrontierPackedScoringBatch(
        started=float(time.perf_counter() if started is None else started),
        stats_inputs=stats_inputs,
        calc_song=calc_song,
        song_inputs=song_inputs,
        ref_arrays=ref_arrays,
        selected_color=str(selected_color or ""),
        primary_color=primary_color,
        secondary_color=secondary_color,
        scoring_bundle=scoring_bundle,
        scoring_bundle_ms=scoring_bundle_ms,
        base_components=base_components,
        ft_values=np.ascontiguousarray(ft_values, dtype=np.int32),
        ff_values=np.ascontiguousarray(ff_values, dtype=np.int32),
        residual_values=residual_values,
        frontier_idx_by_stat=frontier_idx_by_stat,
        primary_ftff_delta_values=primary_ftff_delta_values,
        secondary_ftff_delta_values=secondary_ftff_delta_values,
        score_elements_constant=bool(score_elements_constant),
        head_len=int(head_len),
        body_total=int(body_total),
        scoring_setup_ms=setup_ms,
    )


def build_prepared_force_greats_response_frontier_group_arrays_on_owner(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierPackedScoringBatch:
    """Build response group rows + packed scoring surfaces on the GPU owner thread."""
    if batch.group_meta is not None:
        return batch
    from .response_group_build_kernels import build_response_group_rows_gpu

    gb_t0 = time.perf_counter()
    (
        group_meta,
        group_ft,
        group_ff,
        group_ft_stat,
        group_ff_stat,
        candidate_slices_arr,
    ) = build_response_group_rows_gpu(
        batch.base_components,
        batch.ft_values,
        batch.ff_values,
        batch.residual_values,
        batch.frontier_idx_by_stat,
        batch.primary_ftff_delta_values,
        batch.secondary_ftff_delta_values,
        bool(batch.score_elements_constant),
        int(batch.head_len),
        int(batch.body_total),
    )
    group_build_ms = float((time.perf_counter() - gb_t0) * 1000.0)
    kept_stat_keys = _unique_response_stat_keys_tuple(
        group_ft_stat=group_ft_stat,
        group_ff_stat=group_ff_stat,
        frontier_idx_by_stat=batch.frontier_idx_by_stat,
    )
    candidate_slices = tuple(
        (int(row[0]), int(row[1])) for row in np.asarray(candidate_slices_arr, dtype=np.int32)
    )
    (
        scoring_surface_words,
        scoring_surface_counts,
        scoring_surface_head_coeffs,
        scoring_group_offsets,
        scoring_group_lengths,
        scoring_unique_frontiers,
        scoring_surface_compact_ms,
        scoring_surface_head_coeff_ms,
    ) = _pack_scoring_surfaces_for_batch(
        scoring_bundle=batch.scoring_bundle,
        group_meta=group_meta,
        group_ft_stat=group_ft_stat,
        group_ff_stat=group_ff_stat,
    )
    return replace(
        batch,
        group_meta=group_meta,
        group_ft=group_ft,
        group_ff=group_ff,
        group_ft_stat=group_ft_stat,
        group_ff_stat=group_ff_stat,
        candidate_slices=candidate_slices,
        kept_stat_keys=kept_stat_keys,
        scoring_surface_words=scoring_surface_words,
        scoring_surface_counts=scoring_surface_counts,
        scoring_surface_head_coeffs=scoring_surface_head_coeffs,
        scoring_group_offsets=scoring_group_offsets,
        scoring_group_lengths=scoring_group_lengths,
        scoring_unique_frontiers=scoring_unique_frontiers,
        scoring_surface_compact_ms=scoring_surface_compact_ms,
        scoring_surface_head_coeff_ms=scoring_surface_head_coeff_ms,
        scoring_group_build_ms=group_build_ms,
    )


def score_prepared_force_greats_response_frontier_batch_on_gpu_owner(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierOwnerResult:
    """Canonical GPU-owner dispatch: build group rows, score, and return the enriched batch."""
    built_batch = build_prepared_force_greats_response_frontier_group_arrays_on_owner(batch)
    if built_batch.group_meta is None:
        raise RuntimeError("response frontier GPU owner scoring requires built group rows")
    surface_words = built_batch.scoring_surface_words
    surface_counts = built_batch.scoring_surface_counts
    surface_head_coeffs = built_batch.scoring_surface_head_coeffs
    group_offsets = built_batch.scoring_group_offsets
    group_lengths = built_batch.scoring_group_lengths
    if int(group_offsets.shape[0]) != int(built_batch.group_meta.shape[0]) or int(group_lengths.shape[0]) != int(
        built_batch.group_meta.shape[0]
    ):
        raise ValueError("response frontier prepared scoring arrays have inconsistent group lengths")
    if (
        int(surface_words.ndim) != 2
        or int(surface_words.shape[1]) != 8
        or int(surface_counts.ndim) != 2
        or int(surface_counts.shape[1]) != 3
        or int(surface_head_coeffs.ndim) != 2
        or int(surface_head_coeffs.shape[1]) != 4
    ):
        raise ValueError("response frontier prepared scoring arrays have invalid shape")
    inner_rows, _logical_surface_rows = _score_response_group_meta_gpu(
        group_meta=built_batch.group_meta,
        group_offsets=group_offsets,
        group_lengths=group_lengths,
        primary_color=built_batch.primary_color,
        secondary_color=built_batch.secondary_color,
        selected_color=built_batch.selected_color,
        ref_arrays=built_batch.ref_arrays,
        surface_words=surface_words,
        surface_counts=surface_counts,
        surface_head_coeffs=surface_head_coeffs,
    )
    if int(inner_rows.shape[0]) != int(built_batch.group_meta.shape[0]):
        raise ValueError("response frontier exact GPU batch returned the wrong number of group results")
    return FgResponseFrontierOwnerResult(
        batch=built_batch,
        inner_rows=np.asarray(inner_rows, dtype=np.int32),
    )


def materialize_force_greats_response_frontier_owner_result(
    owner_result: FgResponseFrontierOwnerResult,
    *,
    include_forced_counts: bool = False,
) -> list[FgResponseFrontierSolveResult]:
    if not isinstance(owner_result, FgResponseFrontierOwnerResult):
        raise RuntimeError("FG response frontier GPU owner returned an invalid owner result")
    return materialize_prepared_force_greats_response_frontier_batch_results(
        owner_result.batch,
        owner_result.inner_rows,
        include_forced_counts=bool(include_forced_counts),
    )


def run_prepared_force_greats_response_frontier_batches_via_client(
    gpu_client: Any,
    batches: tuple[FgResponseFrontierPackedScoringBatch, ...] | list[FgResponseFrontierPackedScoringBatch],
    *,
    include_forced_counts: bool = False,
) -> list[tuple[list[FgResponseFrontierSolveResult], dict[str, float]]]:
    submitted: list[tuple[Any, dict[str, float]]] = []
    for batch in batches:
        timing: dict[str, float] = {}
        handle = gpu_client.submit_force_greats_response_frontier_score_batch(
            {
                "batch": batch,
                "timing": timing,
            }
        )
        submitted.append((handle, timing))

    prepared_results: list[tuple[list[FgResponseFrontierSolveResult], dict[str, float]]] = []
    for handle, timing in submitted:
        owner_result = handle.future.result()
        materialize_t0 = time.perf_counter()
        results = materialize_force_greats_response_frontier_owner_result(
            owner_result,
            include_forced_counts=bool(include_forced_counts),
        )
        timing["materialize_s"] = max(0.0, time.perf_counter() - float(materialize_t0))
        prepared_results.append((results, timing))
    return prepared_results


def materialize_prepared_force_greats_response_frontier_batch_results(
    batch: FgResponseFrontierPackedScoringBatch,
    inner_rows: np.ndarray,
    *,
    include_forced_counts: bool = False,
) -> list[FgResponseFrontierSolveResult]:
    scoring_bundle = batch.scoring_bundle
    surface_words = batch.scoring_surface_words
    surface_counts = batch.scoring_surface_counts
    group_offsets = batch.scoring_group_offsets
    inner_rows = np.asarray(inner_rows, dtype=np.int32)
    if int(inner_rows.shape[0]) != int(batch.group_meta.shape[0]):
        raise ValueError("response frontier exact GPU batch returned the wrong number of group results")
    out: list[FgResponseFrontierSolveResult] = []
    frontier_by_stat_key: dict[tuple[int, int], FgResponseFrontierResult] = {}
    for candidate_idx, (start, count) in enumerate(batch.candidate_slices):
        if int(count) <= 0:
            raise ValueError("response frontier exact GPU batch produced no pair result")
        local_idx = int(np.argmax(inner_rows[int(start) : int(start) + int(count), 0]))
        row_idx = int(start) + int(local_idx)
        ft = int(batch.group_ft[row_idx])
        ff = int(batch.group_ff[row_idx])
        ft_stat = int(batch.group_ft_stat[row_idx])
        ff_stat = int(batch.group_ff_stat[row_idx])
        stat_key = (int(ft_stat), int(ff_stat))
        frontier = frontier_by_stat_key.get(stat_key)
        if frontier is None:
            frontier = frontier_result_from_scoring_bundle_for_stats(
                batch.calc_song,
                batch.ref_arrays,
                scoring_bundle,
                ft_stat=int(ft_stat),
                ff_stat=int(ff_stat),
            )
            frontier_by_stat_key[stat_key] = frontier
        pair: _ResponsePair = (
            int(ft),
            int(ff),
            frontier,
            float(scoring_bundle.raw_fill_by_ff[ff_stat]),
            float(scoring_bundle.real_time_by_ft[ft_stat]),
        )
        result_row = np.asarray(inner_rows[int(row_idx)], dtype=np.int32).copy()
        result_surface_idx = int(group_offsets[int(row_idx)]) + int(result_row[1])
        result_surface = _surface_from_packed_arrays(
            surface_words=surface_words,
            surface_counts=surface_counts,
            surface_idx=int(result_surface_idx),
        )
        out.append(
            _solve_result_from_row(
                started=float(batch.started),
                base_stats=batch.stats_inputs[int(candidate_idx)],
                selected_color=batch.selected_color,
                song_inputs=batch.song_inputs,
                pair=pair,
                row=result_row,
                surface=result_surface,
                include_forced_counts=bool(include_forced_counts),
            )
        )
    return out


def score_prepared_force_greats_response_frontier_batch_sync(
    batch: FgResponseFrontierPackedScoringBatch,
    *,
    include_forced_counts: bool = False,
) -> list[FgResponseFrontierSolveResult]:
    scoring_bundle_ms = float(batch.scoring_bundle_ms)
    owner_t0 = time.perf_counter()
    owner = score_prepared_force_greats_response_frontier_batch_on_gpu_owner(batch)
    gpu_score_ms = float((time.perf_counter() - owner_t0) * 1000.0)
    batch = owner.batch
    compact_ms = float(batch.scoring_surface_compact_ms)
    head_coeff_ms = float(batch.scoring_surface_head_coeff_ms)
    phase_t0 = time.perf_counter()
    out = materialize_prepared_force_greats_response_frontier_batch_results(
        batch,
        owner.inner_rows,
        include_forced_counts=bool(include_forced_counts),
    )
    result_ms = (time.perf_counter() - phase_t0) * 1000.0
    emit_profile_event(
        component="fg_response_frontier",
        event="score_prepared_batch",
        metrics={
            "scoring_bundle_ms": float(scoring_bundle_ms),
            "scoring_bundle_prepare_ms": float(batch.scoring_bundle_ms),
            "compact_ms": float(compact_ms),
            "head_coeff_ms": float(head_coeff_ms),
            "gpu_score_ms": float(gpu_score_ms),
            "result_ms": float(result_ms),
            "frontier_materialize_ms": float(result_ms),
            "candidate_count": int(len(batch.candidate_slices)),
            "group_count": int(batch.group_meta.shape[0]),
            "kept_stat_keys": int(len(batch.kept_stat_keys)),
            "unique_frontiers": int(batch.scoring_unique_frontiers),
            "surface_rows": int(batch.scoring_surface_words.shape[0]),
            "include_forced_counts": int(bool(include_forced_counts)),
            "cache_source": "bundle",
        },
    )
    return out
