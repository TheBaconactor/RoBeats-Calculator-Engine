from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

import numpy as np

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

from .response_builder import (
    build_force_greats_response_frontier,
    reconstruct_force_greats_response_counts,
    response_surface_dominates,
)
from .response_cache import build_or_load_response_frontier_payload, build_or_load_response_frontier_scoring_bundle
from .response_inner import (
    _pack_response_frontier_surface_pool,
    _score_response_group_meta_gpu,
    optimize_response_frontier_inner_exact,
    optimize_response_frontier_inner_exact_gpu,
    score_response_surface_exact,
)
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
    "build_force_greats_response_frontier",
    "optimize_response_frontier_inner_exact",
    "optimize_response_frontier_inner_exact_gpu",
    "reconstruct_force_greats_response_counts",
    "response_surface_dominates",
    "score_response_surface_exact",
    "solve_force_greats_response_frontier_batch_gpu",
    "solve_force_greats_response_frontier_many_gpu",
]

_InnerStats = tuple[int, int, int, int, int, int, int]
_ResponsePair = tuple[int, int, int, dict[str, Any] | _InnerStats, FgResponseFrontierResult, float, float]


@lru_cache(maxsize=4096)
def _best_response_positions_for_base_ftff(
    *,
    total_budget: int,
    base_ft: int,
    base_ff: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ft_values, ff_values, remaining = ftff_combo_arrays(int(total_budget))
    ft_stat_seq = np.clip(int(base_ft) + (ft_values * GEM_SCALE_FEVER), 0, TOTAL_ROWS).astype(np.int32, copy=False)
    ff_stat_seq = np.clip(int(base_ff) + (ff_values * GEM_SCALE_FEVER), 0, TOTAL_ROWS).astype(np.int32, copy=False)
    canonical_key_seq = ((ft_stat_seq * (TOTAL_ROWS + 1)) + ff_stat_seq).astype(np.int32, copy=False)
    positions = np.arange(int(ft_values.shape[0]), dtype=np.int32)
    unique_keys, first_positions = np.unique(canonical_key_seq, return_index=True)
    if int(unique_keys.shape[0]) == int(canonical_key_seq.shape[0]):
        best_positions = positions
    else:
        sort_order = np.lexsort((positions, -np.asarray(remaining, dtype=np.int32), canonical_key_seq))
        sorted_keys = canonical_key_seq[sort_order]
        first_sorted = np.empty(int(sorted_keys.shape[0]), dtype=np.bool_)
        first_sorted[0] = True
        first_sorted[1:] = sorted_keys[1:] != sorted_keys[:-1]
        best_positions_by_key = sort_order[first_sorted]
        if int(unique_keys.shape[0]) != int(best_positions_by_key.shape[0]):
            raise ValueError("FG response frontier packed prune found inconsistent frontier groups")
        best_positions = best_positions_by_key[np.argsort(first_positions, kind="stable")]
    return (
        np.ascontiguousarray(best_positions, dtype=np.int32),
        np.ascontiguousarray(ft_stat_seq[best_positions], dtype=np.int32),
        np.ascontiguousarray(ff_stat_seq[best_positions], dtype=np.int32),
    )


def _ftff_stat_key(stats_after_ftff: dict[str, Any]) -> tuple[int, int]:
    ff_stat = max(0, min(TOTAL_ROWS, int(stats_after_ftff.get("Fever Fill Rate", 0) or 0)))
    ft_stat = max(0, min(TOTAL_ROWS, int(stats_after_ftff.get("Fever Time", 0) or 0)))
    return int(ft_stat), int(ff_stat)


def _score_elements(stats: dict[str, Any], primary_color: str, secondary_color: str) -> tuple[int, int]:
    if isinstance(stats, tuple):
        return int(stats[3]), int(stats[4])
    return (
        int(stats.get(str(primary_color or ""), 0) or 0),
        int(stats.get(str(secondary_color or ""), 0) or 0),
    )


def _prune_best_positions_by_frontier(
    *,
    positions: np.ndarray,
    frontier_ids: np.ndarray,
    residuals: np.ndarray,
) -> np.ndarray:
    if int(positions.shape[0]) != int(frontier_ids.shape[0]) or int(positions.shape[0]) != int(residuals.shape[0]):
        raise ValueError("FG response frontier best-position prune received inconsistent arrays")
    if int(positions.shape[0]) <= 1:
        return np.ascontiguousarray(positions, dtype=np.int32)

    unique_frontiers, first_positions = np.unique(frontier_ids, return_index=True)
    if int(unique_frontiers.shape[0]) == int(frontier_ids.shape[0]):
        return np.ascontiguousarray(positions, dtype=np.int32)

    sort_order = np.lexsort((positions, -residuals, frontier_ids))
    sorted_frontiers = frontier_ids[sort_order]
    first_sorted = np.empty(int(sorted_frontiers.shape[0]), dtype=np.bool_)
    first_sorted[0] = True
    first_sorted[1:] = sorted_frontiers[1:] != sorted_frontiers[:-1]
    best_local_positions = sort_order[first_sorted]
    if int(unique_frontiers.shape[0]) != int(best_local_positions.shape[0]):
        raise ValueError("FG response frontier packed prune found inconsistent frontier groups")
    kept_local = best_local_positions[np.argsort(first_positions, kind="stable")]
    return np.ascontiguousarray(positions[kept_local], dtype=np.int32)


def _element_ftff_delta(color: str, ft: int, ff: int) -> int:
    if str(color or "") == "Beat":
        return int(ft) * GEM_STAT_TO_ELEMENT_SCALE
    if str(color or "") == "Vibe":
        return int(ff) * GEM_STAT_TO_ELEMENT_SCALE
    return 0


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
        out[primary] = int(base_stats.get(primary, 0) or 0) + _element_ftff_delta(primary, int(ft), int(ff))
    if secondary:
        out[secondary] = int(base_stats.get(secondary, 0) or 0) + _element_ftff_delta(secondary, int(ft), int(ff))
    return out


def _response_pair_dominates(
    a: _ResponsePair,
    b: _ResponsePair,
    *,
    primary_color: str,
    secondary_color: str,
) -> bool:
    if a[4] is not b[4]:
        return False
    if int(a[2]) < int(b[2]):
        return False
    a_primary, a_secondary = _score_elements(a[3], primary_color, secondary_color)
    b_primary, b_secondary = _score_elements(b[3], primary_color, secondary_color)
    return int(a_primary) >= int(b_primary) and int(a_secondary) >= int(b_secondary)


def _prune_dominated_ftff_response_pairs(
    pairs: list[_ResponsePair],
    *,
    primary_color: str,
    secondary_color: str,
) -> list[_ResponsePair]:
    by_frontier: dict[int, list[_ResponsePair]] = {}
    for pair in pairs:
        by_frontier.setdefault(id(pair[4]), []).append(pair)

    out: list[_ResponsePair] = []
    for bucket in by_frontier.values():
        if len(bucket) <= 1:
            out.extend(bucket)
            continue
        first_primary, first_secondary = _score_elements(bucket[0][3], primary_color, secondary_color)
        best_idx = 0
        best_residual = int(bucket[0][2])
        same_score_elements = True
        for idx, pair in enumerate(bucket[1:], start=1):
            primary, secondary = _score_elements(pair[3], primary_color, secondary_color)
            if int(primary) != int(first_primary) or int(secondary) != int(first_secondary):
                same_score_elements = False
                break
            residual = int(pair[2])
            if residual > best_residual:
                best_idx = int(idx)
                best_residual = int(residual)
        if same_score_elements:
            out.append(bucket[best_idx])
            continue

        rows = [
            (
                idx,
                pair,
                int(pair[2]),
                *_score_elements(pair[3], primary_color, secondary_color),
            )
            for idx, pair in enumerate(bucket)
        ]
        rows.sort(key=lambda row: (-row[2], -row[3], -row[4], row[0]))
        skyline: list[tuple[int, int]] = []
        kept_indices: set[int] = set()
        for idx, _pair, _residual, primary, secondary in rows:
            dominated = False
            for kept_primary, kept_secondary in skyline:
                if int(kept_primary) >= int(primary) and int(kept_secondary) >= int(secondary):
                    dominated = True
                    break
            if dominated:
                continue

            write = 0
            for kept_primary, kept_secondary in skyline:
                if int(primary) >= int(kept_primary) and int(secondary) >= int(kept_secondary):
                    continue
                skyline[write] = (kept_primary, kept_secondary)
                write += 1
            del skyline[write:]
            skyline.append((int(primary), int(secondary)))
            kept_indices.add(int(idx))
        out.extend(pair for idx, pair in enumerate(bucket) if int(idx) in kept_indices)
    return out


def _solve_result_from_row(
    *,
    started: float,
    base_stats: dict[str, Any],
    selected_color: str,
    song_inputs: Any,
    ref_arrays: dict[str, Any],
    pair: _ResponsePair,
    row: tuple[int, int, int, int, int, int, int, int, int, int, int],
    include_forced_counts: bool = True,
) -> FgResponseFrontierSolveResult:
    ft, ff, _residual, _stats_after_ftff, frontier, raw_fill, real_fever_time = pair
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
    surface = frontier.first_frontier[int(inner.surface_index)]
    if include_forced_counts:
        forced_counts = reconstruct_force_greats_response_counts(
            frontier=frontier,
            target_surface=surface,
            timestamps=song_inputs.timestamps,
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

    ft_values, ff_values, _remaining = ftff_combo_arrays(int(total_budget))
    if int(ft_values.shape[0]) <= 0:
        raise ValueError("response frontier exact solve found no FT/FF pairs")

    residual_values = np.asarray(_remaining, dtype=np.int32)
    song_inputs = extract_fg_song_inputs(calc_song)
    primary_color = str(song_inputs.primary_color or "")
    secondary_color = str(song_inputs.secondary_color or "")
    ft_seq = tuple(int(v) for v in ft_values)
    ff_seq = tuple(int(v) for v in ff_values)
    residual_seq = tuple(int(v) for v in _remaining)
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
    base_components_by_candidate: list[tuple[int, int, int, int, int, int, int]] = []
    stat_key_seq_by_candidate: list[tuple[np.ndarray, np.ndarray]] = []
    stat_keys: set[tuple[int, int]] = set()
    for base_stats in stats_inputs:
        base_pp = int(base_stats.get("Perfect Points", 0) or 0)
        base_cm = int(base_stats.get("Combo Multiplier", 0) or 0)
        base_fm = int(base_stats.get("Fever Multiplier", 0) or 0)
        base_primary = int(base_stats.get(primary_color, 0) or 0) if primary_color else 0
        base_secondary = int(base_stats.get(secondary_color, 0) or 0) if secondary_color else 0
        base_ft = int(base_stats.get("Fever Time", 0) or 0)
        base_ff = int(base_stats.get("Fever Fill Rate", 0) or 0)
        base_components_by_candidate.append(
            (base_pp, base_cm, base_fm, base_primary, base_secondary, base_ft, base_ff)
        )
        ft_stat_seq = np.clip(base_ft + (ft_values * GEM_SCALE_FEVER), 0, TOTAL_ROWS).astype(np.int32, copy=False)
        ff_stat_seq = np.clip(base_ff + (ff_values * GEM_SCALE_FEVER), 0, TOTAL_ROWS).astype(np.int32, copy=False)
        stat_key_seq_by_candidate.append((ft_stat_seq, ff_stat_seq))
        stat_keys.update(zip(ft_stat_seq.tolist(), ff_stat_seq.tolist()))

    head_len = min(int(song_inputs.total_notes), 100)
    body_total = max(0, int(song_inputs.total_notes) - 100)
    if score_elements_constant and not include_forced_counts:
        scoring_bundle = build_or_load_response_frontier_scoring_bundle(calc_song, ref_arrays, stat_keys=stat_keys)
        frontier_idx_by_stat = scoring_bundle.frontier_idx_by_stat
        complete_scoring_bundle = len(scoring_bundle.frontier_idx_by_key) >= (TOTAL_ROWS + 1) * (TOTAL_ROWS + 1)

        pair_positions = np.arange(int(ft_values.shape[0]), dtype=np.int32)
        group_meta_blocks: list[np.ndarray] = []
        group_offset_blocks: list[np.ndarray] = []
        group_length_blocks: list[np.ndarray] = []
        group_ft_blocks: list[np.ndarray] = []
        group_ff_blocks: list[np.ndarray] = []
        group_ft_stat_blocks: list[np.ndarray] = []
        group_ff_stat_blocks: list[np.ndarray] = []
        group_frontier_blocks: list[np.ndarray] = []
        candidate_slices: list[tuple[int, int]] = []
        group_start = 0
        for candidate_idx, components in enumerate(base_components_by_candidate):
            base_pp, base_cm, base_fm, base_primary, base_secondary, base_ft, base_ff = components
            if complete_scoring_bundle:
                ft_stat_seq, ff_stat_seq = stat_key_seq_by_candidate[int(candidate_idx)]
                frontier_idx_seq = frontier_idx_by_stat[ft_stat_seq, ff_stat_seq]
                best_positions, kept_ft_stats, kept_ff_stats = _best_response_positions_for_base_ftff(
                    total_budget=int(total_budget),
                    base_ft=int(base_ft),
                    base_ff=int(base_ff),
                )
                best_positions = _prune_best_positions_by_frontier(
                    positions=best_positions,
                    frontier_ids=np.ascontiguousarray(frontier_idx_seq[best_positions], dtype=np.int32),
                    residuals=np.ascontiguousarray(residual_values[best_positions], dtype=np.int32),
                )
                kept_ft_stats = np.ascontiguousarray(ft_stat_seq[best_positions], dtype=np.int32)
                kept_ff_stats = np.ascontiguousarray(ff_stat_seq[best_positions], dtype=np.int32)
                kept_frontiers = np.ascontiguousarray(frontier_idx_seq[best_positions], dtype=np.int32)
            else:
                ft_stat_seq, ff_stat_seq = stat_key_seq_by_candidate[int(candidate_idx)]
                frontier_idx_seq = frontier_idx_by_stat[ft_stat_seq, ff_stat_seq]
                best_positions = _prune_best_positions_by_frontier(
                    positions=pair_positions,
                    frontier_ids=frontier_idx_seq,
                    residuals=residual_values,
                )
                kept_ft_stats = np.ascontiguousarray(ft_stat_seq[best_positions], dtype=np.int32)
                kept_ff_stats = np.ascontiguousarray(ff_stat_seq[best_positions], dtype=np.int32)
                kept_frontiers = np.ascontiguousarray(frontier_idx_seq[best_positions], dtype=np.int32)
            if bool(np.any(kept_frontiers < 0)):
                raise ValueError("FG response frontier stat key was not loaded for packed batch solve")
            kept_count = int(best_positions.shape[0])
            if kept_count <= 0:
                raise ValueError("response frontier exact GPU batch produced no pair result")

            meta = np.empty((kept_count, 8), dtype=np.int32)
            meta[:, 0] = residual_values[best_positions]
            meta[:, 1] = int(base_pp)
            meta[:, 2] = int(base_cm)
            meta[:, 3] = int(base_fm)
            meta[:, 4] = int(base_primary)
            meta[:, 5] = int(base_secondary)
            meta[:, 6] = int(head_len)
            meta[:, 7] = int(body_total)
            lengths = np.ascontiguousarray(scoring_bundle.frontier_lengths[kept_frontiers], dtype=np.int32)
            if bool(np.any(lengths <= 0)):
                raise ValueError("FG response frontier payload contains an empty first frontier")

            group_meta_blocks.append(meta)
            group_offset_blocks.append(np.ascontiguousarray(scoring_bundle.frontier_offsets[kept_frontiers], dtype=np.int32))
            group_length_blocks.append(lengths)
            group_ft_blocks.append(np.ascontiguousarray(ft_values[best_positions], dtype=np.int32))
            group_ff_blocks.append(np.ascontiguousarray(ff_values[best_positions], dtype=np.int32))
            group_ft_stat_blocks.append(kept_ft_stats)
            group_ff_stat_blocks.append(kept_ff_stats)
            group_frontier_blocks.append(np.ascontiguousarray(kept_frontiers, dtype=np.int32))
            candidate_slices.append((int(group_start), int(kept_count)))
            group_start += int(kept_count)

        group_meta = np.ascontiguousarray(np.concatenate(group_meta_blocks, axis=0), dtype=np.int32)
        group_offsets_arr = np.ascontiguousarray(np.concatenate(group_offset_blocks, axis=0), dtype=np.int32)
        group_lengths_arr = np.ascontiguousarray(np.concatenate(group_length_blocks, axis=0), dtype=np.int32)
        group_ft = np.concatenate(group_ft_blocks, axis=0).astype(np.int32, copy=False)
        group_ff = np.concatenate(group_ff_blocks, axis=0).astype(np.int32, copy=False)
        group_ft_stat = np.concatenate(group_ft_stat_blocks, axis=0).astype(np.int32, copy=False)
        group_ff_stat = np.concatenate(group_ff_stat_blocks, axis=0).astype(np.int32, copy=False)
        group_frontier_idx = np.concatenate(group_frontier_blocks, axis=0).astype(np.int32, copy=False)

        inner_rows, _surface_rows = _score_response_group_meta_gpu(
            group_meta=group_meta,
            group_offsets=group_offsets_arr,
            group_lengths=group_lengths_arr,
            primary_color=primary_color,
            secondary_color=secondary_color,
            selected_color=str(selected_color or ""),
            ref_arrays=ref_arrays,
            surface_words=scoring_bundle.surface_words,
            surface_counts=scoring_bundle.surface_counts,
        )
        if int(inner_rows.shape[0]) != int(group_meta.shape[0]):
            raise ValueError("response frontier exact GPU batch returned the wrong number of group results")

        out: list[FgResponseFrontierSolveResult] = []
        for candidate_idx, (start, count) in enumerate(candidate_slices):
            if int(count) <= 0:
                raise ValueError("response frontier exact GPU batch produced no pair result")
            local_idx = int(np.argmax(inner_rows[int(start) : int(start) + int(count), 0]))
            row_idx = int(start) + int(local_idx)
            ft = int(group_ft[row_idx])
            ff = int(group_ff[row_idx])
            ft_stat = int(group_ft_stat[row_idx])
            ff_stat = int(group_ff_stat[row_idx])
            frontier_idx = int(group_frontier_idx[row_idx])
            surface_row_idx = int(scoring_bundle.frontier_offsets[frontier_idx]) + int(inner_rows[int(row_idx), 1])
            surface = FgResponseSurface(
                int(scoring_bundle.surface_words[surface_row_idx, 0]),
                int(scoring_bundle.surface_words[surface_row_idx, 1]),
                int(scoring_bundle.surface_words[surface_row_idx, 2]),
                int(scoring_bundle.surface_words[surface_row_idx, 3]),
                int(scoring_bundle.surface_words[surface_row_idx, 4]),
                int(scoring_bundle.surface_words[surface_row_idx, 5]),
                int(scoring_bundle.surface_words[surface_row_idx, 6]),
                int(scoring_bundle.surface_words[surface_row_idx, 7]),
                int(scoring_bundle.surface_counts[surface_row_idx, 0]),
                int(scoring_bundle.surface_counts[surface_row_idx, 1]),
            )
            frontier = FgResponseFrontierResult((surface,), {}, 0, 0, 0, 0, 1, 1, 0, 0.0)
            stats_after_ftff: _InnerStats = (
                int(group_meta[row_idx, 1]),
                int(group_meta[row_idx, 2]),
                int(group_meta[row_idx, 3]),
                int(group_meta[row_idx, 4]),
                int(group_meta[row_idx, 5]),
                int(ft_stat),
                int(ff_stat),
            )
            pair: _ResponsePair = (
                int(ft),
                int(ff),
                int(group_meta[row_idx, 0]),
                stats_after_ftff,
                frontier,
                float(scoring_bundle.raw_fill_by_ff[ff_stat]),
                float(scoring_bundle.real_time_by_ft[ft_stat]),
            )
            result_row = np.asarray(inner_rows[int(row_idx)], dtype=np.int32).copy()
            result_row[1] = 0
            out.append(
                _solve_result_from_row(
                    started=started,
                    base_stats=stats_inputs[int(candidate_idx)],
                    selected_color=str(selected_color or ""),
                    song_inputs=song_inputs,
                    ref_arrays=ref_arrays,
                    pair=pair,
                    row=result_row,
                    include_forced_counts=bool(include_forced_counts),
                )
            )
        return out

    payload = build_or_load_response_frontier_payload(
        calc_song,
        ref_arrays,
        stat_keys=stat_keys,
        include_state_frontiers=bool(include_forced_counts),
    ).payload
    frontiers = payload.frontiers
    frontier_idx_by_id = {id(frontier): int(idx) for idx, frontier in enumerate(frontiers)}
    surface_words, surface_counts, frontier_offsets, frontier_lengths = _pack_response_frontier_surface_pool(
        frontiers,
        total_notes=int(song_inputs.total_notes),
    )

    group_meta_rows: list[tuple[int, int, int, int, int, int, int, int]] = []
    group_offsets_list: list[int] = []
    group_lengths_list: list[int] = []
    group_owners: list[tuple[int, _ResponsePair]] = []
    for candidate_idx, (components, stat_key_seqs) in enumerate(
        zip(base_components_by_candidate, stat_key_seq_by_candidate, strict=True)
    ):
        base_pp, base_cm, base_fm, base_primary, base_secondary, base_ft, base_ff = components
        ft_stat_seq, ff_stat_seq = stat_key_seqs
        if score_elements_constant:
            best_pair_by_frontier: dict[int, _ResponsePair] = {}
            for ft, ff, residual, ft_stat, ff_stat in zip(
                ft_seq,
                ff_seq,
                residual_seq,
                ft_stat_seq,
                ff_stat_seq,
                strict=True,
            ):
                frontier = payload.frontier_by_key.get((ft_stat, ff_stat))
                if frontier is None:
                    raise ValueError(f"FG response frontier stat key was not loaded: {(ft_stat, ff_stat)}")
                marker = id(frontier)
                current = best_pair_by_frontier.get(marker)
                if current is not None and int(residual) <= int(current[2]):
                    continue
                stats_after_ftff: _InnerStats = (
                    int(base_pp),
                    int(base_cm),
                    int(base_fm),
                    int(base_primary),
                    int(base_secondary),
                    int(ft_stat),
                    int(ff_stat),
                )
                best_pair_by_frontier[marker] = (
                    int(ft),
                    int(ff),
                    int(residual),
                    stats_after_ftff,
                    frontier,
                    float(payload.raw_fill_by_ff[ff_stat]),
                    float(payload.real_time_by_ft[ft_stat]),
                )
            pair_records = list(best_pair_by_frontier.values())
        else:
            pair_records = []
            for ft, ff, residual, ft_stat, ff_stat in zip(
                ft_seq,
                ff_seq,
                residual_seq,
                ft_stat_seq,
                ff_stat_seq,
                strict=True,
            ):
                primary_value = base_primary + int(ft) * primary_ft_delta + int(ff) * primary_ff_delta
                secondary_value = base_secondary + int(ft) * secondary_ft_delta + int(ff) * secondary_ff_delta
                stats_after_ftff = (
                    int(base_pp),
                    int(base_cm),
                    int(base_fm),
                    int(primary_value),
                    int(secondary_value),
                    int(ft_stat),
                    int(ff_stat),
                )
                frontier = payload.frontier_by_key.get((ft_stat, ff_stat))
                if frontier is None:
                    raise ValueError(f"FG response frontier stat key was not loaded: {(ft_stat, ff_stat)}")
                pair_records.append(
                    (
                        int(ft),
                        int(ff),
                        int(residual),
                        stats_after_ftff,
                        frontier,
                        float(payload.raw_fill_by_ff[ff_stat]),
                        float(payload.real_time_by_ft[ft_stat]),
                    )
                )
            pair_records = _prune_dominated_ftff_response_pairs(
                pair_records,
                primary_color=primary_color,
                secondary_color=secondary_color,
            )
        for pair in pair_records:
            _ft, _ff, residual, stats_after_ftff, frontier, _raw_fill, _real_fever_time = pair
            frontier_idx = frontier_idx_by_id.get(id(frontier))
            if frontier_idx is None:
                raise ValueError("FG response frontier payload is missing a packed frontier index")
            length = int(frontier_lengths[int(frontier_idx)])
            if length <= 0:
                raise ValueError("FG response frontier payload contains an empty first frontier")
            residual_i = int(residual)
            if residual_i < 0:
                residual_i = 0
            group_meta_rows.append(
                (
                    int(residual_i),
                    int(stats_after_ftff[0]),
                    int(stats_after_ftff[1]),
                    int(stats_after_ftff[2]),
                    int(stats_after_ftff[3]),
                    int(stats_after_ftff[4]),
                    int(head_len),
                    int(body_total),
                )
            )
            group_offsets_list.append(int(frontier_offsets[int(frontier_idx)]))
            group_lengths_list.append(int(length))
            group_owners.append((int(candidate_idx), pair))

    if group_meta_rows:
        group_meta = np.asarray(group_meta_rows, dtype=np.int32)
        group_offsets_arr = np.asarray(group_offsets_list, dtype=np.int32)
        group_lengths_arr = np.asarray(group_lengths_list, dtype=np.int32)
    else:
        group_meta = np.zeros((0, 8), dtype=np.int32)
        group_offsets_arr = np.zeros((0,), dtype=np.int32)
        group_lengths_arr = np.zeros((0,), dtype=np.int32)
    inner_rows, _surface_rows = _score_response_group_meta_gpu(
        group_meta=group_meta,
        group_offsets=group_offsets_arr,
        group_lengths=group_lengths_arr,
        primary_color=primary_color,
        secondary_color=secondary_color,
        selected_color=str(selected_color or ""),
        ref_arrays=ref_arrays,
        surface_words=surface_words,
        surface_counts=surface_counts,
    )
    if int(inner_rows.shape[0]) != len(group_owners):
        raise ValueError("response frontier exact GPU batch returned the wrong number of group results")

    best_by_candidate: list[tuple[_ResponsePair, int] | None] = [None] * len(stats_inputs)
    for group_idx, owner in enumerate(group_owners):
        candidate_idx, pair = owner
        current = best_by_candidate[int(candidate_idx)]
        if current is None or int(inner_rows[group_idx, 0]) > int(inner_rows[int(current[1]), 0]):
            best_by_candidate[int(candidate_idx)] = (pair, int(group_idx))

    out: list[FgResponseFrontierSolveResult] = []
    for candidate_idx, best in enumerate(best_by_candidate):
        if best is None:
            raise ValueError("response frontier exact GPU batch produced no pair result")
        pair, row_idx = best
        out.append(
            _solve_result_from_row(
                started=started,
                base_stats=stats_inputs[int(candidate_idx)],
                selected_color=str(selected_color or ""),
                song_inputs=song_inputs,
                ref_arrays=ref_arrays,
                pair=pair,
                row=inner_rows[int(row_idx)],
                include_forced_counts=bool(include_forced_counts),
            )
        )
    return out


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
