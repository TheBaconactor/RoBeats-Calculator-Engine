from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import time
from typing import Any

import numpy as np

from gear_optimizer.solver.timing_envelope import TimedSong
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import GEM_BUDGET, MAX_STAT, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER
from gear_optimizer.core.gem_defs import build_gem_counts
from gear_optimizer.solver.force_greats_common import response_frontier_base_components_row
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
from gear_optimizer.stats import apply_gems, gems

from .response_builder import reconstruct_force_greats_response_trace
from .response_cache import load_response_frontier_scoring_bundle
from .response_cache_serde import frontier_result_from_scoring_bundle_for_stats
from .response_cache_store import load_first_surface_scoring_patterns
from .response_cache_types import FgResponseFrontierScoringBundle, all_response_stat_keys
from .response_gem_search import _score_response_group_meta_cpu, build_response_group_rows
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
    "FgBatchStage",
    "FgResponseFrontierPackedScoringBatch",
    "FgScoreRow",
    "score_fg_base_components",
    "fg_solve_result",
    "fg_solve_results",
    "fg_batch_stage",
    "required_response_stat_keys_for_scoring_batch",
    "prepare_force_greats_response_frontier_scoring_batch",
    "build_prepared_force_greats_response_frontier_group_arrays",
    "build_prepared_force_greats_response_frontier_group_rows",
    "pack_prepared_force_greats_response_frontier_scoring_surfaces",
    "reconstruct_force_greats_response_trace",
]

_ResponsePair = tuple[int, int, FgResponseFrontierResult, float, float]


def _required_response_stat_keys(
    base_components: np.ndarray,
    ft_values: np.ndarray,
    ff_values: np.ndarray,
) -> tuple[tuple[int, int], ...]:
    """Return every clipped FT/FF cell reachable by the exact candidate batch."""
    components = np.asarray(base_components, dtype=np.int32)
    ft_gems = np.asarray(ft_values, dtype=np.int32).reshape(-1)
    ff_gems = np.asarray(ff_values, dtype=np.int32).reshape(-1)
    if components.ndim != 2 or int(components.shape[1]) != 7:
        raise ValueError("response frontier base_components must have shape (N, 7)")
    if int(components.shape[0]) <= 0:
        raise ValueError("response frontier stat-key reachability requires at least one candidate")
    if ft_gems.shape != ff_gems.shape or int(ft_gems.shape[0]) <= 0:
        raise ValueError("response frontier FT/FF gem arrays must be aligned and non-empty")

    ft_stats = np.clip(
        components[:, 5, None] + (ft_gems[None, :] * int(STAT_GEM_GAIN_FEVER)),
        0,
        int(MAX_STAT),
    )
    ff_stats = np.clip(
        components[:, 6, None] + (ff_gems[None, :] * int(STAT_GEM_GAIN_FEVER)),
        0,
        int(MAX_STAT),
    )
    axis = int(MAX_STAT) + 1
    encoded = np.asarray((ft_stats * axis) + ff_stats, dtype=np.int32).reshape(-1)
    unique_encoded = np.unique(encoded)
    return tuple((int(value // axis), int(value % axis)) for value in unique_encoded)


def required_response_stat_keys_for_scoring_batch(
    *,
    base_stats_list: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    total_budget: int = GEM_BUDGET,
    base_stats7_list: list[Any] | tuple[Any, ...] | None = None,
) -> tuple[tuple[int, int], ...]:
    """Return the exact response-cache cells addressable by a scoring batch.

    This is a reachability projection of the canonical candidate inputs and the complete
    ``ftff_combo_arrays`` search space. It removes no candidate and performs no score-based
    pruning; cells outside this set cannot be indexed by the corresponding exact solve.
    """
    stats_inputs = tuple(dict(stats) for stats in (base_stats_list or []))
    if not stats_inputs:
        raise ValueError("response frontier stat-key reachability requires at least one candidate")
    if base_stats7_list is None:
        base_stats7_inputs: tuple[Any, ...] = (None,) * len(stats_inputs)
    else:
        base_stats7_inputs = tuple(base_stats7_list)
        if len(base_stats7_inputs) != len(stats_inputs):
            raise ValueError(
                "response frontier base_stats7_list must align 1:1 with base_stats_list "
                f"({len(base_stats7_inputs)} != {len(stats_inputs)})"
            )
    base_components = np.asarray(
        [
            response_frontier_base_components_row(
                base_stats,
                base_stats7,
                primary_color="",
                secondary_color="",
            )
            for base_stats, base_stats7 in zip(stats_inputs, base_stats7_inputs, strict=True)
        ],
        dtype=np.int32,
    )
    ft_values, ff_values, _remaining = ftff_combo_arrays(int(total_budget))
    return _required_response_stat_keys(base_components, ft_values, ff_values)


class FgBatchStage(Enum):
    INPUT = "input"
    GROUP_BUILT = "group_built"
    SURFACES_PACKED = "surfaces_packed"


def fg_batch_stage(batch: FgResponseFrontierPackedScoringBatch) -> FgBatchStage:
    if batch.scoring_surface_pattern_ids is not None:
        return FgBatchStage.SURFACES_PACKED
    if batch.group_meta is not None:
        return FgBatchStage.GROUP_BUILT
    return FgBatchStage.INPUT


@dataclass(frozen=True, slots=True)
class FgResponseFrontierPackedScoringBatch:
    started: float
    stats_inputs: tuple[dict[str, Any], ...]
    song: TimedSong
    song_inputs: Any
    curves: StatCurves
    selected_color: str
    primary_color: str
    secondary_color: str
    scoring_bundle: FgResponseFrontierScoringBundle
    scoring_bundle_ms: float
    # Prep inputs of the group rows (build_prepared_force_greats_response_frontier_group_rows).
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
    scoring_surface_pattern_ids: np.ndarray | None = None
    scoring_surface_pattern_words: np.ndarray | None = None
    scoring_surface_counts: np.ndarray | None = None
    scoring_surface_pattern_head_coeffs: np.ndarray | None = None
    scoring_group_offsets: np.ndarray | None = None
    scoring_group_lengths: np.ndarray | None = None
    scoring_unique_frontiers: int = 0
    scoring_surface_compact_ms: float = 0.0
    scoring_surface_head_coeff_ms: float = 0.0
    scoring_setup_ms: float = 0.0
    scoring_group_build_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class FgScoreRow:
    """A loadout's FG gem-search winner: its FT/FF gems and stat keys, the 11-int gem-search row (best score, surface
    index, PP/CM/FM/element gems, final PP/CM/FM/primary/secondary) and the winning surface (11 ints). fg_solve_result
    turns it into the full solve result with the loadout's pre-gem stats."""

    ft: int
    ff: int
    ft_stat: int
    ff_stat: int
    inner_row: tuple[int, ...]
    surface: tuple[int, ...]


def _surface_from_packed_arrays(
    *,
    surface_pattern_ids: np.ndarray,
    surface_pattern_words: np.ndarray,
    surface_counts: np.ndarray,
    surface_idx: int,
) -> FgResponseSurface:
    idx = int(surface_idx)
    if idx < 0 or idx >= int(surface_pattern_ids.shape[0]) or idx >= int(surface_counts.shape[0]):
        raise ValueError("response frontier exact selected surface is outside the packed pool")
    pattern_idx = int(surface_pattern_ids[idx])
    if pattern_idx < 0 or pattern_idx >= int(surface_pattern_words.shape[0]):
        raise ValueError("response frontier exact selected surface has an invalid head-pattern ID")
    word_row = np.asarray(surface_pattern_words[pattern_idx], dtype=np.uint32)
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
        raise ValueError("response frontier group metadata has inconsistent head length")
    unique_frontiers = np.ascontiguousarray(np.unique(kept_frontiers), dtype=np.int32)

    full_surface_pattern_ids = np.asarray(scoring_bundle.surface_pattern_ids)
    full_surface_pattern_words = np.asarray(scoring_bundle.surface_pattern_words)
    full_surface_counts = np.asarray(scoring_bundle.surface_counts)
    full_surface_pattern_head_coeffs = np.asarray(scoring_bundle.surface_pattern_head_coeffs)
    if int(full_surface_pattern_ids.shape[0]) > 0:
        if (
            int(full_surface_pattern_ids.ndim) != 1
            or int(full_surface_pattern_words.ndim) != 2
            or int(full_surface_pattern_words.shape[1]) != 8
            or int(full_surface_counts.ndim) != 2
            or int(full_surface_counts.shape[0]) != int(full_surface_pattern_ids.shape[0])
            or int(full_surface_counts.shape[1]) != 3
            or int(full_surface_pattern_head_coeffs.ndim) != 2
            or int(full_surface_pattern_head_coeffs.shape[0]) != int(full_surface_pattern_words.shape[0])
            or int(full_surface_pattern_head_coeffs.shape[1]) != 4
        ):
            raise ValueError("FG response frontier scoring bundle has invalid in-memory surface arrays")
        # In-memory (session-pruned) pools are scored in place through absolute frontier offsets,
        # like response_cache_serde does; the scorers validate the whole pool's IDs and counts.
        surface_pattern_ids = full_surface_pattern_ids
        surface_pattern_words = full_surface_pattern_words
        surface_counts = full_surface_counts
        surface_pattern_head_coeffs = full_surface_pattern_head_coeffs
        group_offsets = np.ascontiguousarray(frontier_offsets_all[kept_frontiers], dtype=np.int32)
        group_ends = group_offsets.astype(np.int64) + group_lengths
        if bool(np.any(group_offsets < 0)) or bool(np.any(group_ends > int(full_surface_pattern_ids.shape[0]))):
            raise ValueError("FG response frontier selected a range outside the in-memory surface pool")
    else:
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
        (
            surface_pattern_ids,
            surface_counts,
            surface_pattern_words,
            surface_pattern_head_coeffs,
        ) = load_first_surface_scoring_patterns(
            scoring_bundle.cache_key,
            ranges,
            surface_generation=scoring_bundle.surface_generation,
            bundle_path=scoring_bundle.bundle_path,
        )
    compact_ms = float((time.perf_counter() - phase_t0) * 1000.0)
    head_coeff_ms = 0.0
    if (
        int(surface_pattern_ids.ndim) != 1
        or int(surface_pattern_ids.shape[0]) != int(surface_counts.shape[0])
        or int(surface_pattern_words.ndim) != 2
        or int(surface_pattern_words.shape[1]) != 8
        or int(surface_pattern_head_coeffs.ndim) != 2
        or int(surface_pattern_head_coeffs.shape[0]) != int(surface_pattern_words.shape[0])
        or int(surface_pattern_head_coeffs.shape[1]) != 4
    ):
        raise ValueError("FG response frontier scoring bundle has invalid compact surface arrays")
    return (
        np.ascontiguousarray(surface_pattern_ids, dtype=np.int32),
        np.ascontiguousarray(surface_pattern_words, dtype=np.uint32),
        np.ascontiguousarray(surface_counts, dtype=np.int32),
        np.ascontiguousarray(surface_pattern_head_coeffs, dtype=np.int32),
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
    axis = int(MAX_STAT) + 1
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


def _solve_result_from_row(
    *,
    base_stats: dict[str, Any],
    selected_color: str,
    pair: _ResponsePair,
    row: tuple[int, int, int, int, int, int, int, int, int, int, int],
    surface: FgResponseSurface,
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
    final_stats = apply_gems(
        base_stats,
        gems(pp=inner.g_pp, cm=inner.g_cm, fm=inner.g_fm, ft=ft, ff=ff, element=inner.g_ov),
        selected_color,
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
        seconds=0.0,
        raw_fever_fill=float(raw_fill),
        real_fever_time=float(real_fever_time),
    )


def prepare_force_greats_response_frontier_scoring_batch(
    *,
    base_stats_list: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
    base_stats7_list: list[Any] | tuple[Any, ...] | None = None,
    total_budget: int = GEM_BUDGET,
    started: float | None = None,
    scoring_bundle: FgResponseFrontierScoringBundle | None = None,
) -> FgResponseFrontierPackedScoringBatch:
    """Prepare the FG candidate inputs of score_fg_base_components (group rows and scoring surfaces are built by
    build_prepared_force_greats_response_frontier_group_arrays).

    ``base_stats7_list`` (when given) carries each candidate's authoritative base
    components by origin: the GPU-native GA pack kernel's device-computed
    ``base_stats7`` for GA candidates, ``None`` for dict-sourced (DB-best/skyline)
    candidates. It must align 1:1 with ``base_stats_list``. The single canonical
    per-candidate rule lives in ``response_frontier_base_components_row``; the full
    ``BaseStats`` dicts are still retained as ``stats_inputs`` for result
    materialization (post-gem stats span all 10 keys, not just the 7 scored ones)."""
    setup_t0 = time.perf_counter()
    stats_inputs = tuple(dict(stats) for stats in (base_stats_list or []))
    if not stats_inputs:
        raise ValueError("response frontier exact scoring batch requires at least one candidate")

    if base_stats7_list is None:
        base_stats7_inputs: tuple[Any, ...] = (None,) * len(stats_inputs)
    else:
        base_stats7_inputs = tuple(base_stats7_list)
        if len(base_stats7_inputs) != len(stats_inputs):
            raise ValueError(
                "response frontier base_stats7_list must align 1:1 with base_stats_list "
                f"({len(base_stats7_inputs)} != {len(stats_inputs)})"
            )

    ft_values, ff_values, remaining = ftff_combo_arrays(int(total_budget))
    if int(ft_values.shape[0]) <= 0:
        raise ValueError("response frontier exact solve found no FT/FF pairs")

    residual_values = np.asarray(remaining, dtype=np.int32)
    song_inputs = song.fg_inputs
    primary_color = str(song_inputs.primary_color or "")
    secondary_color = str(song_inputs.secondary_color or "")
    primary_ft_delta = STAT_GEM_ELEMENT_GAIN if primary_color == "Beat" else 0
    primary_ff_delta = STAT_GEM_ELEMENT_GAIN if primary_color == "Vibe" else 0
    secondary_ft_delta = STAT_GEM_ELEMENT_GAIN if secondary_color == "Beat" else 0
    secondary_ff_delta = STAT_GEM_ELEMENT_GAIN if secondary_color == "Vibe" else 0
    score_elements_constant = (
        primary_ft_delta == 0
        and primary_ff_delta == 0
        and secondary_ft_delta == 0
        and secondary_ff_delta == 0
    )
    base_components = np.ascontiguousarray(
        np.asarray(
            [
                response_frontier_base_components_row(
                    base_stats,
                    base_stats7,
                    primary_color=primary_color,
                    secondary_color=secondary_color,
                )
                for base_stats, base_stats7 in zip(stats_inputs, base_stats7_inputs, strict=True)
            ],
            dtype=np.int32,
        )
    )
    bundle_t0 = time.perf_counter()
    if scoring_bundle is None:
        scoring_bundle = load_response_frontier_scoring_bundle(
            song,
            curves,
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
        song=song,
        song_inputs=song_inputs,
        curves=curves,
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


def build_prepared_force_greats_response_frontier_group_rows(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierPackedScoringBatch:
    """The batch with its loadouts' gem-search groups (response_gem_search.build_response_group_rows)."""
    if fg_batch_stage(batch) is not FgBatchStage.INPUT:
        return batch
    gb_t0 = time.perf_counter()
    (
        group_meta,
        group_ft,
        group_ff,
        group_ft_stat,
        group_ff_stat,
        candidate_slices_arr,
    ) = build_response_group_rows(
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
    return replace(
        batch,
        group_meta=group_meta,
        group_ft=group_ft,
        group_ff=group_ff,
        group_ft_stat=group_ft_stat,
        group_ff_stat=group_ff_stat,
        candidate_slices=candidate_slices,
        kept_stat_keys=kept_stat_keys,
        scoring_group_build_ms=group_build_ms,
    )


def pack_prepared_force_greats_response_frontier_scoring_surfaces(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierPackedScoringBatch:
    """The batch with the scoring surfaces of its groups packed."""
    if fg_batch_stage(batch) is FgBatchStage.INPUT:
        raise RuntimeError("FG response frontier surface pack requires built group rows")
    if fg_batch_stage(batch) is FgBatchStage.SURFACES_PACKED:
        return batch
    (
        scoring_surface_pattern_ids,
        scoring_surface_pattern_words,
        scoring_surface_counts,
        scoring_surface_pattern_head_coeffs,
        scoring_group_offsets,
        scoring_group_lengths,
        scoring_unique_frontiers,
        scoring_surface_compact_ms,
        scoring_surface_head_coeff_ms,
    ) = _pack_scoring_surfaces_for_batch(
        scoring_bundle=batch.scoring_bundle,
        group_meta=batch.group_meta,
        group_ft_stat=np.asarray(batch.group_ft_stat, dtype=np.int32),
        group_ff_stat=np.asarray(batch.group_ff_stat, dtype=np.int32),
    )
    return replace(
        batch,
        scoring_surface_pattern_ids=scoring_surface_pattern_ids,
        scoring_surface_pattern_words=scoring_surface_pattern_words,
        scoring_surface_counts=scoring_surface_counts,
        scoring_surface_pattern_head_coeffs=scoring_surface_pattern_head_coeffs,
        scoring_group_offsets=scoring_group_offsets,
        scoring_group_lengths=scoring_group_lengths,
        scoring_unique_frontiers=scoring_unique_frontiers,
        scoring_surface_compact_ms=scoring_surface_compact_ms,
        scoring_surface_head_coeff_ms=scoring_surface_head_coeff_ms,
    )


def build_prepared_force_greats_response_frontier_group_arrays(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierPackedScoringBatch:
    """The batch with its group rows built and their scoring surfaces packed."""
    built = build_prepared_force_greats_response_frontier_group_rows(batch)
    return pack_prepared_force_greats_response_frontier_scoring_surfaces(built)


def _score_packed_batch(batch: FgResponseFrontierPackedScoringBatch, floors: np.ndarray | None) -> np.ndarray:
    """The gem-search rows of a packed batch (CPU cores); with `floors` (a score per loadout) a loadout's row is exact
    only when it reaches its floor."""
    if fg_batch_stage(batch) is not FgBatchStage.SURFACES_PACKED:
        raise RuntimeError(
            "FG response frontier owner score requires a finalized batch "
            "(group rows built and scoring surfaces packed before submit)"
        )
    return _score_response_group_meta_cpu(
        group_meta=batch.group_meta,
        group_offsets=batch.scoring_group_offsets,
        group_lengths=batch.scoring_group_lengths,
        candidate_slices=batch.candidate_slices,
        primary_color=batch.primary_color,
        secondary_color=batch.secondary_color,
        selected_color=batch.selected_color,
        curves=batch.curves,
        surface_pattern_ids=batch.scoring_surface_pattern_ids,
        surface_pattern_words=batch.scoring_surface_pattern_words,
        surface_counts=batch.scoring_surface_counts,
        surface_pattern_head_coeffs=batch.scoring_surface_pattern_head_coeffs,
        floors=floors,
    )


def _score_rows_from_batch(batch: FgResponseFrontierPackedScoringBatch, inner_rows: np.ndarray) -> list[FgScoreRow]:
    """Each loadout's winner (its first group with the highest score), in batch order."""
    out: list[FgScoreRow] = []
    for start, count in batch.candidate_slices:
        row_idx = int(start) + int(np.argmax(inner_rows[int(start) : int(start) + int(count), 0]))
        row = inner_rows[row_idx]
        surface = _surface_from_packed_arrays(
            surface_pattern_ids=batch.scoring_surface_pattern_ids,
            surface_pattern_words=batch.scoring_surface_pattern_words,
            surface_counts=batch.scoring_surface_counts,
            surface_idx=int(batch.scoring_group_offsets[row_idx]) + int(row[1]),
        )
        out.append(
            FgScoreRow(
                ft=int(batch.group_ft[row_idx]),
                ff=int(batch.group_ff[row_idx]),
                ft_stat=int(batch.group_ft_stat[row_idx]),
                ff_stat=int(batch.group_ff_stat[row_idx]),
                inner_row=tuple(int(v) for v in row),
                surface=tuple(int(v) for v in surface),
            )
        )
    return out


def score_fg_base_components(
    *,
    base_components: np.ndarray,
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
    scoring_bundle: FgResponseFrontierScoringBundle,
    total_budget: int = GEM_BUDGET,
    floors: np.ndarray | None = None,
) -> dict[tuple[int, ...], FgScoreRow]:
    """The FG score row of each distinct 7-vector of pre-gem totals (PP, CM, FM, primary, secondary, FT, FF), keyed by
    it (CPU only); equal 7-vectors have equal FG results, so each is scored once. ``selected_color`` is the song's
    selected element; every other input is song-level (the scoring bundle). With `floors` (a score per row) a row is
    exact only when it reaches its floor (the lowest of a 7-vector's floors); below it, its score is only known to be
    lower."""
    floor_of: dict[tuple[int, ...], int] = {}
    for idx, row in enumerate(np.asarray(base_components, dtype=np.int32).tolist()):
        key = tuple(row)
        floor = -1 if floors is None else int(floors[idx])
        floor_of[key] = min(floor_of.get(key, floor), floor)
    unique_rows = list(floor_of)
    if not unique_rows:
        return {}
    batch = prepare_force_greats_response_frontier_scoring_batch(
        # Placeholders: base_stats7 is the scored vector (response_frontier_base_components_row).
        base_stats_list=[
            {"Perfect Points": row[0], "Combo Multiplier": row[1], "Fever Multiplier": row[2], "Fever Time": row[5],
             "Fever Fill Rate": row[6]}
            for row in unique_rows
        ],
        base_stats7_list=unique_rows,
        song=song,
        curves=curves,
        selected_color=str(selected_color or ""),
        total_budget=int(total_budget),
        scoring_bundle=scoring_bundle,
    )
    built = build_prepared_force_greats_response_frontier_group_arrays(batch)
    inner_rows = _score_packed_batch(built, None if floors is None else np.asarray(list(floor_of.values())))
    return dict(zip(unique_rows, _score_rows_from_batch(built, inner_rows), strict=True))


def fg_solve_result(
    *,
    score_row: FgScoreRow,
    base_stats: dict[str, Any],
    selected_color: str,
    song: TimedSong,
    curves: StatCurves,
    scoring_bundle: FgResponseFrontierScoringBundle,
    frontier_by_stat_key: dict[tuple[int, int], FgResponseFrontierResult],
) -> FgResponseFrontierSolveResult:
    """A loadout's FG solve result from its score row and its pre-gem stats (all 10). The frontier of the winning stat
    key comes from the scoring bundle, once per key for the callers sharing `frontier_by_stat_key`."""
    stat_key = (score_row.ft_stat, score_row.ff_stat)
    frontier = frontier_by_stat_key.get(stat_key)
    if frontier is None:
        frontier = frontier_result_from_scoring_bundle_for_stats(
            song, curves, scoring_bundle, ft_stat=score_row.ft_stat, ff_stat=score_row.ff_stat
        )
        frontier_by_stat_key[stat_key] = frontier
    pair: _ResponsePair = (
        score_row.ft,
        score_row.ff,
        frontier,
        float(scoring_bundle.raw_fill_by_ff[score_row.ff_stat]),
        float(scoring_bundle.real_time_by_ft[score_row.ft_stat]),
    )
    return _solve_result_from_row(
        base_stats=base_stats,
        selected_color=str(selected_color or ""),
        pair=pair,
        row=score_row.inner_row,
        surface=FgResponseSurface(*score_row.surface),
    )


def fg_solve_results(
    stats_rows,
    *,
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
    scoring_bundle: FgResponseFrontierScoringBundle,
    total_budget: int = GEM_BUDGET,
) -> list[FgResponseFrontierSolveResult]:
    """Each stats row's FG solve result: rows of pre-gem stats re-solve the gems within total_budget; with
    total_budget=0 the rows are allocated stats and only the FG plan is solved."""
    song_inputs = song.fg_inputs
    totals = [
        response_frontier_base_components_row(
            stats, None, primary_color=song_inputs.primary_color, secondary_color=song_inputs.secondary_color
        )
        for stats in stats_rows
    ]
    rows = score_fg_base_components(
        base_components=np.asarray(totals, dtype=np.int32), song=song, curves=curves, selected_color=selected_color,
        scoring_bundle=scoring_bundle, total_budget=total_budget,
    )
    frontiers: dict[tuple[int, int], FgResponseFrontierResult] = {}
    return [
        fg_solve_result(score_row=rows[key], base_stats=dict(stats), selected_color=selected_color, song=song,
                        curves=curves, scoring_bundle=scoring_bundle, frontier_by_stat_key=frontiers)
        for key, stats in zip(totals, stats_rows, strict=True)
    ]
