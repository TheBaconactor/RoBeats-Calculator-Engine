from __future__ import annotations

from dataclasses import dataclass
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
from gear_optimizer.core.jit_setup import jit
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
    "prepare_force_greats_response_frontier_scoring_batch",
    "score_prepared_force_greats_response_frontier_batch_gpu",
    "reconstruct_force_greats_response_counts",
    "reconstruct_force_greats_response_trace",
    "solve_force_greats_response_frontier_batch_gpu",
    "solve_force_greats_response_frontier_many_gpu",
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
    kept_stat_keys: tuple[tuple[int, int], ...]
    scoring_bundle: FgResponseFrontierScoringBundle
    scoring_bundle_ms: float
    group_meta: np.ndarray
    group_ft: np.ndarray
    group_ff: np.ndarray
    group_ft_stat: np.ndarray
    group_ff_stat: np.ndarray
    candidate_slices: tuple[tuple[int, int], ...]
    scoring_surface_words: np.ndarray
    scoring_surface_counts: np.ndarray
    scoring_surface_head_coeffs: np.ndarray
    scoring_group_offsets: np.ndarray
    scoring_group_lengths: np.ndarray
    scoring_unique_frontiers: int
    scoring_surface_compact_ms: float
    scoring_surface_head_coeff_ms: float
    scoring_setup_ms: float = 0.0
    scoring_geometry_ms: float = 0.0
    scoring_group_build_ms: float = 0.0
    scoring_concat_ms: float = 0.0


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


@jit(nopython=True, cache=True)
def _clip_response_stat(value: int) -> int:
    if int(value) < 0:
        return 0
    if int(value) > TOTAL_ROWS:
        return TOTAL_ROWS
    return int(value)


@jit(nopython=True, cache=True)
def _build_response_group_rows_numba(
    base_components: np.ndarray,
    ft_values: np.ndarray,
    ff_values: np.ndarray,
    residual_values: np.ndarray,
    frontier_idx_by_stat: np.ndarray,
    primary_ftff_delta_values: np.ndarray,
    secondary_ftff_delta_values: np.ndarray,
    score_elements_constant: bool,
    head_len: int,
    body_total: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    candidate_count = int(base_components.shape[0])
    pair_count = int(ft_values.shape[0])
    if candidate_count <= 0 or pair_count <= 0:
        raise ValueError("response frontier exact group builder received no work")

    max_frontier = -1
    for ft_stat in range(int(frontier_idx_by_stat.shape[0])):
        for ff_stat in range(int(frontier_idx_by_stat.shape[1])):
            fid = int(frontier_idx_by_stat[ft_stat, ff_stat])
            if fid > max_frontier:
                max_frontier = fid
    if max_frontier < 0:
        raise ValueError("response frontier exact group builder received no loaded frontiers")

    keep_mask = np.zeros((candidate_count, pair_count), dtype=np.bool_)
    keep_counts = np.zeros((candidate_count,), dtype=np.int32)
    head = np.empty((max_frontier + 1,), dtype=np.int32)
    tail = np.empty((max_frontier + 1,), dtype=np.int32)
    next_idx = np.empty((pair_count,), dtype=np.int32)
    ordered_frontiers = np.empty((pair_count,), dtype=np.int32)
    best_pos = np.empty((max_frontier + 1,), dtype=np.int32)
    best_residual = np.empty((max_frontier + 1,), dtype=np.int32)

    for candidate_idx in range(candidate_count):
        base_primary = int(base_components[candidate_idx, 3])
        base_secondary = int(base_components[candidate_idx, 4])
        base_ft = int(base_components[candidate_idx, 5])
        base_ff = int(base_components[candidate_idx, 6])
        if bool(score_elements_constant):
            for fid in range(max_frontier + 1):
                best_pos[fid] = -1
                best_residual[fid] = -2147483648
            for pos in range(pair_count):
                ft_stat = _clip_response_stat(base_ft + (int(ft_values[pos]) * GEM_SCALE_FEVER))
                ff_stat = _clip_response_stat(base_ff + (int(ff_values[pos]) * GEM_SCALE_FEVER))
                frontier_id = int(frontier_idx_by_stat[ft_stat, ff_stat])
                if frontier_id < 0:
                    raise ValueError("FG response frontier prewarmed scoring bundle does not cover requested stat keys")
                residual = int(residual_values[pos])
                current_pos = int(best_pos[frontier_id])
                if current_pos < 0 or residual > int(best_residual[frontier_id]) or (
                    residual == int(best_residual[frontier_id]) and pos < current_pos
                ):
                    best_pos[frontier_id] = pos
                    best_residual[frontier_id] = residual
            kept_count = 0
            for pos in range(pair_count):
                ft_stat = _clip_response_stat(base_ft + (int(ft_values[pos]) * GEM_SCALE_FEVER))
                ff_stat = _clip_response_stat(base_ff + (int(ff_values[pos]) * GEM_SCALE_FEVER))
                frontier_id = int(frontier_idx_by_stat[ft_stat, ff_stat])
                if int(best_pos[frontier_id]) == pos:
                    keep_mask[candidate_idx, pos] = True
                    kept_count += 1
            keep_counts[candidate_idx] = kept_count
            continue

        for fid in range(max_frontier + 1):
            head[fid] = -1
            tail[fid] = -1
        for pos in range(pair_count):
            next_idx[pos] = -1
        ordered_count = 0
        for pos in range(pair_count):
            ft_stat = _clip_response_stat(base_ft + (int(ft_values[pos]) * GEM_SCALE_FEVER))
            ff_stat = _clip_response_stat(base_ff + (int(ff_values[pos]) * GEM_SCALE_FEVER))
            frontier_id = int(frontier_idx_by_stat[ft_stat, ff_stat])
            if frontier_id < 0:
                raise ValueError("FG response frontier prewarmed scoring bundle does not cover requested stat keys")
            if int(head[frontier_id]) < 0:
                head[frontier_id] = pos
                tail[frontier_id] = pos
                ordered_frontiers[ordered_count] = frontier_id
                ordered_count += 1
            else:
                next_idx[int(tail[frontier_id])] = pos
                tail[frontier_id] = pos

        kept_count = 0
        for order_idx in range(ordered_count):
            frontier_id = int(ordered_frontiers[order_idx])
            first = int(head[frontier_id])
            first_primary = base_primary + int(primary_ftff_delta_values[first])
            first_secondary = base_secondary + int(secondary_ftff_delta_values[first])
            same_score_elements = True
            best_idx = first
            best_res = int(residual_values[first])
            row = int(next_idx[first])
            while row >= 0:
                primary = base_primary + int(primary_ftff_delta_values[row])
                secondary = base_secondary + int(secondary_ftff_delta_values[row])
                if primary != first_primary or secondary != first_secondary:
                    same_score_elements = False
                    break
                residual = int(residual_values[row])
                if residual > best_res:
                    best_idx = row
                    best_res = residual
                row = int(next_idx[row])
            if same_score_elements:
                keep_mask[candidate_idx, best_idx] = True
                kept_count += 1
                continue

            row = first
            while row >= 0:
                row_residual = int(residual_values[row])
                row_primary = base_primary + int(primary_ftff_delta_values[row])
                row_secondary = base_secondary + int(secondary_ftff_delta_values[row])
                dominated = False
                other = first
                while other >= 0:
                    if other != row:
                        other_residual = int(residual_values[other])
                        other_primary = base_primary + int(primary_ftff_delta_values[other])
                        other_secondary = base_secondary + int(secondary_ftff_delta_values[other])
                        if (
                            other_residual >= row_residual
                            and other_primary >= row_primary
                            and other_secondary >= row_secondary
                            and (
                                other_residual > row_residual
                                or other_primary > row_primary
                                or other_secondary > row_secondary
                                or other < row
                            )
                        ):
                            dominated = True
                            break
                    other = int(next_idx[other])
                if not dominated:
                    keep_mask[candidate_idx, row] = True
                    kept_count += 1
                row = int(next_idx[row])
        keep_counts[candidate_idx] = kept_count

    total_count = 0
    for candidate_idx in range(candidate_count):
        count = int(keep_counts[candidate_idx])
        if count <= 0:
            raise ValueError("response frontier exact GPU batch produced no pair result")
        total_count += count

    group_meta = np.empty((total_count, 8), dtype=np.int32)
    group_ft = np.empty((total_count,), dtype=np.int32)
    group_ff = np.empty((total_count,), dtype=np.int32)
    group_ft_stat = np.empty((total_count,), dtype=np.int32)
    group_ff_stat = np.empty((total_count,), dtype=np.int32)
    candidate_slices = np.empty((candidate_count, 2), dtype=np.int32)
    write = 0
    for candidate_idx in range(candidate_count):
        base_pp = int(base_components[candidate_idx, 0])
        base_cm = int(base_components[candidate_idx, 1])
        base_fm = int(base_components[candidate_idx, 2])
        base_primary = int(base_components[candidate_idx, 3])
        base_secondary = int(base_components[candidate_idx, 4])
        base_ft = int(base_components[candidate_idx, 5])
        base_ff = int(base_components[candidate_idx, 6])
        candidate_start = write

        for fid in range(max_frontier + 1):
            head[fid] = -1
            tail[fid] = -1
            best_pos[fid] = -1
            best_residual[fid] = -2147483648
        for pos in range(pair_count):
            next_idx[pos] = -1
        ordered_count = 0
        for pos in range(pair_count):
            ft_stat = _clip_response_stat(base_ft + (int(ft_values[pos]) * GEM_SCALE_FEVER))
            ff_stat = _clip_response_stat(base_ff + (int(ff_values[pos]) * GEM_SCALE_FEVER))
            frontier_id = int(frontier_idx_by_stat[ft_stat, ff_stat])
            if frontier_id < 0:
                raise ValueError("FG response frontier prewarmed scoring bundle does not cover requested stat keys")
            if int(head[frontier_id]) < 0:
                head[frontier_id] = pos
                tail[frontier_id] = pos
                ordered_frontiers[ordered_count] = frontier_id
                ordered_count += 1
            else:
                next_idx[int(tail[frontier_id])] = pos
                tail[frontier_id] = pos
            if bool(score_elements_constant):
                residual = int(residual_values[pos])
                current_pos = int(best_pos[frontier_id])
                if current_pos < 0 or residual > int(best_residual[frontier_id]) or (
                    residual == int(best_residual[frontier_id]) and pos < current_pos
                ):
                    best_pos[frontier_id] = pos
                    best_residual[frontier_id] = residual

        for order_idx in range(ordered_count):
            frontier_id = int(ordered_frontiers[order_idx])
            if bool(score_elements_constant):
                pos = int(best_pos[frontier_id])
                if pos < 0:
                    continue
                ft = int(ft_values[pos])
                ff = int(ff_values[pos])
                ft_stat = _clip_response_stat(base_ft + (ft * GEM_SCALE_FEVER))
                ff_stat = _clip_response_stat(base_ff + (ff * GEM_SCALE_FEVER))
                group_meta[write, 0] = int(residual_values[pos])
                group_meta[write, 1] = base_pp
                group_meta[write, 2] = base_cm
                group_meta[write, 3] = base_fm
                group_meta[write, 4] = base_primary + int(primary_ftff_delta_values[pos])
                group_meta[write, 5] = base_secondary + int(secondary_ftff_delta_values[pos])
                group_meta[write, 6] = int(head_len)
                group_meta[write, 7] = int(body_total)
                group_ft[write] = ft
                group_ff[write] = ff
                group_ft_stat[write] = ft_stat
                group_ff_stat[write] = ff_stat
                write += 1
                continue

            row = int(head[frontier_id])
            while row >= 0:
                if bool(keep_mask[candidate_idx, row]):
                    ft = int(ft_values[row])
                    ff = int(ff_values[row])
                    ft_stat = _clip_response_stat(base_ft + (ft * GEM_SCALE_FEVER))
                    ff_stat = _clip_response_stat(base_ff + (ff * GEM_SCALE_FEVER))
                    group_meta[write, 0] = int(residual_values[row])
                    group_meta[write, 1] = base_pp
                    group_meta[write, 2] = base_cm
                    group_meta[write, 3] = base_fm
                    group_meta[write, 4] = base_primary + int(primary_ftff_delta_values[row])
                    group_meta[write, 5] = base_secondary + int(secondary_ftff_delta_values[row])
                    group_meta[write, 6] = int(head_len)
                    group_meta[write, 7] = int(body_total)
                    group_ft[write] = ft
                    group_ff[write] = ff
                    group_ft_stat[write] = ft_stat
                    group_ff_stat[write] = ff_stat
                    write += 1
                row = int(next_idx[row])
        candidate_slices[candidate_idx, 0] = candidate_start
        candidate_slices[candidate_idx, 1] = write - candidate_start
    return group_meta, group_ft, group_ff, group_ft_stat, group_ff_stat, candidate_slices


@jit(nopython=True, cache=True)
def _requested_response_stat_keys_numba(
    base_components: np.ndarray,
    ft_values: np.ndarray,
    ff_values: np.ndarray,
) -> np.ndarray:
    seen = np.zeros((TOTAL_ROWS + 1, TOTAL_ROWS + 1), dtype=np.bool_)
    requested_count = 0
    for candidate_idx in range(int(base_components.shape[0])):
        base_ft = int(base_components[candidate_idx, 5])
        base_ff = int(base_components[candidate_idx, 6])
        for pos in range(int(ft_values.shape[0])):
            ft_stat = _clip_response_stat(base_ft + (int(ft_values[pos]) * GEM_SCALE_FEVER))
            ff_stat = _clip_response_stat(base_ff + (int(ff_values[pos]) * GEM_SCALE_FEVER))
            if not seen[ft_stat, ff_stat]:
                seen[ft_stat, ff_stat] = True
                requested_count += 1

    out = np.empty((requested_count, 2), dtype=np.int32)
    write = 0
    for ft_stat in range(TOTAL_ROWS + 1):
        for ff_stat in range(TOTAL_ROWS + 1):
            if seen[ft_stat, ff_stat]:
                out[write, 0] = int(ft_stat)
                out[write, 1] = int(ff_stat)
                write += 1
    return out


_GROUP_ROW_BUILDER_WARMED = False


def warmup_response_frontier_group_builder() -> None:
    global _GROUP_ROW_BUILDER_WARMED
    if bool(_GROUP_ROW_BUILDER_WARMED):
        return
    ft_values, ff_values, residual_values = ftff_combo_arrays(2)
    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    for pos in range(int(ft_values.shape[0])):
        ft_stat = min(TOTAL_ROWS, int(ft_values[pos]) * GEM_SCALE_FEVER)
        ff_stat = min(TOTAL_ROWS, int(ff_values[pos]) * GEM_SCALE_FEVER)
        frontier_idx_by_stat[ft_stat, ff_stat] = int(pos)
    base_components = np.asarray([[0, 0, 0, 1, 2, 0, 0]], dtype=np.int32)
    primary_delta = np.asarray(ft_values * GEM_STAT_TO_ELEMENT_SCALE, dtype=np.int32)
    secondary_delta = np.asarray(ff_values * GEM_STAT_TO_ELEMENT_SCALE, dtype=np.int32)
    requested = _requested_response_stat_keys_numba(
        np.ascontiguousarray(base_components, dtype=np.int32),
        np.ascontiguousarray(ft_values, dtype=np.int32),
        np.ascontiguousarray(ff_values, dtype=np.int32),
    )
    group_meta, group_ft, group_ff, group_ft_stat, group_ff_stat, candidate_slices = _build_response_group_rows_numba(
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
    expected_requested = sorted(
        (int(ft), int(ff))
        for ft, ff in np.column_stack(
            (
                (ft_values * GEM_SCALE_FEVER).astype(np.int32, copy=False),
                (ff_values * GEM_SCALE_FEVER).astype(np.int32, copy=False),
            )
        ).tolist()
    )
    if (
        sorted((int(row[0]), int(row[1])) for row in requested.tolist()) != expected_requested
        or int(group_meta.shape[0]) != int(ft_values.shape[0])
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
    ref_arrays: dict[str, Any],
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
    setup_ms = float((time.perf_counter() - setup_t0) * 1000.0)
    geometry_t0 = time.perf_counter()
    frontier_idx_by_stat = np.ascontiguousarray(scoring_bundle.frontier_idx_by_stat, dtype=np.int32)
    geometry_ms = float((time.perf_counter() - geometry_t0) * 1000.0)
    primary_ftff_delta_values = np.asarray(
        (ft_values * int(primary_ft_delta)) + (ff_values * int(primary_ff_delta)),
        dtype=np.int32,
    )
    secondary_ftff_delta_values = np.asarray(
        (ft_values * int(secondary_ft_delta)) + (ff_values * int(secondary_ff_delta)),
        dtype=np.int32,
    )
    group_build_t0 = time.perf_counter()
    (
        group_meta,
        group_ft,
        group_ff,
        group_ft_stat,
        group_ff_stat,
        candidate_slices_arr,
    ) = _build_response_group_rows_numba(
        base_components,
        np.ascontiguousarray(ft_values, dtype=np.int32),
        np.ascontiguousarray(ff_values, dtype=np.int32),
        residual_values,
        frontier_idx_by_stat,
        np.ascontiguousarray(primary_ftff_delta_values, dtype=np.int32),
        np.ascontiguousarray(secondary_ftff_delta_values, dtype=np.int32),
        bool(score_elements_constant),
        int(head_len),
        int(body_total),
    )
    group_build_ms = float((time.perf_counter() - group_build_t0) * 1000.0)
    concat_t0 = time.perf_counter()
    kept_stat_keys_tuple = _unique_response_stat_keys_tuple(
        group_ft_stat=group_ft_stat,
        group_ff_stat=group_ff_stat,
        frontier_idx_by_stat=frontier_idx_by_stat,
    )
    candidate_slices = tuple((int(row[0]), int(row[1])) for row in np.asarray(candidate_slices_arr, dtype=np.int32))
    concat_ms = float((time.perf_counter() - concat_t0) * 1000.0)
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
        scoring_bundle=scoring_bundle,
        group_meta=group_meta,
        group_ft_stat=group_ft_stat,
        group_ff_stat=group_ff_stat,
    )
    return FgResponseFrontierPackedScoringBatch(
        started=float(time.perf_counter() if started is None else started),
        stats_inputs=stats_inputs,
        calc_song=calc_song,
        song_inputs=song_inputs,
        ref_arrays=ref_arrays,
        selected_color=str(selected_color or ""),
        primary_color=primary_color,
        secondary_color=secondary_color,
        kept_stat_keys=kept_stat_keys_tuple,
        scoring_bundle=scoring_bundle,
        scoring_bundle_ms=scoring_bundle_ms,
        group_meta=group_meta,
        group_ft=group_ft,
        group_ff=group_ff,
        group_ft_stat=group_ft_stat,
        group_ff_stat=group_ff_stat,
        candidate_slices=candidate_slices,
        scoring_surface_words=scoring_surface_words,
        scoring_surface_counts=scoring_surface_counts,
        scoring_surface_head_coeffs=scoring_surface_head_coeffs,
        scoring_group_offsets=scoring_group_offsets,
        scoring_group_lengths=scoring_group_lengths,
        scoring_unique_frontiers=scoring_unique_frontiers,
        scoring_surface_compact_ms=scoring_surface_compact_ms,
        scoring_surface_head_coeff_ms=scoring_surface_head_coeff_ms,
        scoring_setup_ms=setup_ms,
        scoring_geometry_ms=geometry_ms,
        scoring_group_build_ms=group_build_ms,
        scoring_concat_ms=concat_ms,
    )


def score_prepared_force_greats_response_frontier_batch_raw_gpu(
    batch: FgResponseFrontierPackedScoringBatch,
    *,
    include_forced_counts: bool = False,
) -> np.ndarray:
    _ = include_forced_counts
    surface_words = batch.scoring_surface_words
    surface_counts = batch.scoring_surface_counts
    surface_head_coeffs = batch.scoring_surface_head_coeffs
    group_offsets = batch.scoring_group_offsets
    group_lengths = batch.scoring_group_lengths
    if int(group_offsets.shape[0]) != int(batch.group_meta.shape[0]) or int(group_lengths.shape[0]) != int(
        batch.group_meta.shape[0]
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
        group_meta=batch.group_meta,
        group_offsets=group_offsets,
        group_lengths=group_lengths,
        primary_color=batch.primary_color,
        secondary_color=batch.secondary_color,
        selected_color=batch.selected_color,
        ref_arrays=batch.ref_arrays,
        surface_words=surface_words,
        surface_counts=surface_counts,
        surface_head_coeffs=surface_head_coeffs,
    )
    if int(inner_rows.shape[0]) != int(batch.group_meta.shape[0]):
        raise ValueError("response frontier exact GPU batch returned the wrong number of group results")
    return np.asarray(inner_rows, dtype=np.int32)


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
                ref_arrays=batch.ref_arrays,
                pair=pair,
                row=result_row,
                surface=result_surface,
                include_forced_counts=bool(include_forced_counts),
            )
        )
    return out


def score_prepared_force_greats_response_frontier_batch_gpu(
    batch: FgResponseFrontierPackedScoringBatch,
    *,
    include_forced_counts: bool = False,
) -> list[FgResponseFrontierSolveResult]:
    phase_t0 = time.perf_counter()
    _scoring_bundle = batch.scoring_bundle
    scoring_bundle_ms = (time.perf_counter() - phase_t0) * 1000.0
    payload_ms = 0.0
    compact_ms = float(batch.scoring_surface_compact_ms)
    head_coeff_ms = float(batch.scoring_surface_head_coeff_ms)
    phase_t0 = time.perf_counter()
    inner_rows = score_prepared_force_greats_response_frontier_batch_raw_gpu(batch)
    gpu_score_ms = (time.perf_counter() - phase_t0) * 1000.0
    phase_t0 = time.perf_counter()
    out = materialize_prepared_force_greats_response_frontier_batch_results(
        batch,
        inner_rows,
        include_forced_counts=bool(include_forced_counts),
    )
    result_ms = (time.perf_counter() - phase_t0) * 1000.0
    emit_profile_event(
        component="fg_response_frontier",
        event="score_prepared_batch",
        metrics={
            "payload_ms": float(payload_ms),
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


def solve_force_greats_response_frontier_many_gpu(
    *,
    base_stats_list: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_color: str,
    total_budget: int = TOTAL_GEM_BUDGET,
    include_forced_counts: bool = True,
) -> list[FgResponseFrontierSolveResult]:
    started = time.perf_counter()
    stats_inputs = [dict(stats) for stats in (base_stats_list or [])]
    if not stats_inputs:
        return []

    batch = prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=stats_inputs,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=selected_color,
        total_budget=int(total_budget),
        started=started,
    )
    return score_prepared_force_greats_response_frontier_batch_gpu(
        batch,
        include_forced_counts=bool(include_forced_counts),
    )


def solve_force_greats_response_frontier_batch_gpu(
    *,
    base_stats: dict[str, Any],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_color: str,
    total_budget: int = TOTAL_GEM_BUDGET,
) -> FgResponseFrontierSolveResult:
    results = solve_force_greats_response_frontier_many_gpu(
        base_stats_list=[base_stats],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=selected_color,
        total_budget=int(total_budget),
    )
    if not results:
        raise ValueError("response frontier exact GPU batch produced no pair result")
    return results[0]
