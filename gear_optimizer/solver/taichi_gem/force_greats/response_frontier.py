from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import sys
import time
from typing import TYPE_CHECKING, Any

import numpy as np

from gear_optimizer.core.profile_events import emit_profile_event, profile_events_active
from gear_optimizer.core.constants import (
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    TOTAL_GEM_BUDGET,
    TOTAL_ROWS,
)
from gear_optimizer.core.gem_defs import build_gem_counts
from gear_optimizer.solver.force_greats_common import response_frontier_base_components_row
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
from .response_inner_host import _score_response_group_meta_cpu, _score_response_group_meta_gpu  # noqa: F401
from .response_types import (
    FgResponseFrontierResult,
    FgResponseFrontierSolveResult,
    FgResponseInnerResult,
    FgResponseSurface,
)

if TYPE_CHECKING:
    from gear_optimizer.solver.gpu_service import GpuJobHandle

__all__ = [
    "FgResponseFrontierResult",
    "FgResponseFrontierSolveResult",
    "FgResponseInnerResult",
    "FgResponseSurface",
    "FgBatchStage",
    "FgResponseFrontierPackedScoringBatch",
    "FgResponseFrontierOwnerResult",
    "FgFusedOwnerScoreRow",
    "resolve_fused_owner_score_rows_from_batch",
    "score_fused_owner_base_components_on_gpu_owner",
    "build_fused_owner_solve_result_from_score_row",
    "fg_batch_stage",
    "FG_BATCH_MISSING_GROUP_ROWS_MSG",
    "batch_needs_async_group_build_prefetch",
    "assert_batch_has_group_build_prefetch_or_rows",
    "prepare_force_greats_response_frontier_scoring_batch",
    "build_prepared_force_greats_response_frontier_group_arrays_on_owner",
    "build_prepared_force_greats_response_frontier_group_rows_on_owner",
    "pack_prepared_force_greats_response_frontier_scoring_surfaces",
    "finalize_prepared_force_greats_response_frontier_batch_for_gpu_score",
    "score_prepared_force_greats_response_frontier_batch_on_gpu_owner",
    "score_prepared_force_greats_response_frontier_batch_on_cpu_owner",
    "score_prepared_force_greats_response_frontier_batch_sync",
    "score_prepared_force_greats_response_frontier_batch_cpu_sync",
    "materialize_force_greats_response_frontier_owner_result",
    "reconstruct_force_greats_response_counts",
    "reconstruct_force_greats_response_trace",
]

_ResponsePair = tuple[int, int, FgResponseFrontierResult, float, float]


class FgBatchStage(Enum):
    INPUT = "input"
    GROUP_BUILT = "group_built"
    SURFACES_PACKED = "surfaces_packed"


def fg_batch_stage(batch: FgResponseFrontierPackedScoringBatch) -> FgBatchStage:
    if batch.scoring_surface_words is not None:
        return FgBatchStage.SURFACES_PACKED
    if batch.group_meta is not None:
        return FgBatchStage.GROUP_BUILT
    return FgBatchStage.INPUT


FG_BATCH_MISSING_GROUP_ROWS_MSG = (
    "FG response frontier batch is missing group rows; "
    "async group-build prefetch must run during FG prep"
)


def batch_needs_async_group_build_prefetch(batch: FgResponseFrontierPackedScoringBatch) -> bool:
    return fg_batch_stage(batch) is FgBatchStage.INPUT and batch.group_build_handle is None


def assert_batch_has_group_build_prefetch_or_rows(batch: FgResponseFrontierPackedScoringBatch) -> None:
    if batch_needs_async_group_build_prefetch(batch):
        raise RuntimeError(FG_BATCH_MISSING_GROUP_ROWS_MSG)


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
    # Host-side prep inputs; group rows are built on the GPU owner, surfaces packed on FG workers.
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
    # In-process only: optional async group-build submitted during FG prep.
    group_build_handle: GpuJobHandle | None = None


@dataclass(frozen=True, slots=True)
class FgResponseFrontierOwnerResult:
    batch: FgResponseFrontierPackedScoringBatch
    inner_rows: np.ndarray


@dataclass(frozen=True, slots=True)
class FgFusedOwnerScoreRow:
    """The owner-computable FG solve result for ONE base_components 7-vector.

    The fused GA->FG handoff (Slice 3) scores on the GPU owner straight from the
    device ``base_stats7`` (== base_components), but cannot materialize the final
    ``FgResponseFrontierSolveResult``: materialization needs the full 10-key
    BaseStats dict (``apply_gems_to_base_stats`` over all stats) which lives only
    on the host decode side. This record carries exactly the owner-resolved,
    full-dict-INDEPENDENT pieces the driver materializer needs to finish the
    result without any further GPU work:

    * ``ft`` / ``ff``: the winning FT/FF gem counts,
    * ``ft_stat`` / ``ff_stat``: the winning fever stat keys (the driver
      reconstructs the frontier from these + the song-level scoring bundle),
    * ``inner_row``: the 11-int inner result row
      ``[best_score, surface_index, g_pp, g_cm, g_fm, g_ov, final_pp, final_cm,
      final_fm, final_primary, final_secondary]``,
    * ``surface``: the resolved winning ``FgResponseSurface`` (11 ints), extracted
      on the owner from its packed surfaces.

    Every field is a plain int / int-tuple (picklable). Keyed by the
    base_components 7-tuple, which the driver re-derives identically from the same
    device base_stats7 (Slice 2 bit-exactness)."""

    ft: int
    ff: int
    ft_stat: int
    ff_stat: int
    inner_row: tuple[int, ...]
    surface: tuple[int, ...]


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
            perfect_floor_timestamps=song_inputs.perfect_floor,
            great_floor_timestamps=song_inputs.great_floor,
            lanes=song_inputs.lanes,
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
    base_stats7_list: list[Any] | tuple[Any, ...] | None = None,
    total_budget: int = TOTAL_GEM_BUDGET,
    started: float | None = None,
    scoring_bundle: FgResponseFrontierScoringBundle | None = None,
) -> FgResponseFrontierPackedScoringBatch:
    """Prepare the GA->FG candidate inputs (host, prep thread). The group rows + scoring
    surfaces are built later on the GPU owner thread by
    `score_prepared_force_greats_response_frontier_batch_on_gpu_owner`.

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


def _resolve_async_group_build_handle(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierPackedScoringBatch:
    if fg_batch_stage(batch) is not FgBatchStage.INPUT:
        return batch
    handle = batch.group_build_handle
    if handle is None:
        return batch
    built_batch = handle.future.result()
    if fg_batch_stage(built_batch) is FgBatchStage.INPUT:
        raise RuntimeError("FG response frontier async group-build completed without group rows")
    return built_batch


def build_prepared_force_greats_response_frontier_group_rows_on_owner(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierPackedScoringBatch:
    """Build pruned group rows on the GPU owner thread (Taichi kernels only)."""
    batch = _resolve_async_group_build_handle(batch)
    if fg_batch_stage(batch) is not FgBatchStage.INPUT:
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
        group_build_handle=None,
    )


def pack_prepared_force_greats_response_frontier_scoring_surfaces(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierPackedScoringBatch:
    """Pack compact scoring surfaces on a CPU worker thread (not the GPU owner)."""
    if fg_batch_stage(batch) is FgBatchStage.INPUT:
        raise RuntimeError("FG response frontier surface pack requires built group rows")
    if fg_batch_stage(batch) is FgBatchStage.SURFACES_PACKED:
        return batch
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
        group_meta=batch.group_meta,
        group_ft_stat=np.asarray(batch.group_ft_stat, dtype=np.int32),
        group_ff_stat=np.asarray(batch.group_ff_stat, dtype=np.int32),
    )
    return replace(
        batch,
        scoring_surface_words=scoring_surface_words,
        scoring_surface_counts=scoring_surface_counts,
        scoring_surface_head_coeffs=scoring_surface_head_coeffs,
        scoring_group_offsets=scoring_group_offsets,
        scoring_group_lengths=scoring_group_lengths,
        scoring_unique_frontiers=scoring_unique_frontiers,
        scoring_surface_compact_ms=scoring_surface_compact_ms,
        scoring_surface_head_coeff_ms=scoring_surface_head_coeff_ms,
    )


def finalize_prepared_force_greats_response_frontier_batch_for_gpu_score(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierPackedScoringBatch:
    """
    Resolve any async group-build handle and pack scoring surfaces on the caller thread.

    Production FG workers call this before submitting the GPU score request so the owner
    thread only runs Taichi scoring kernels.
    """
    batch = _resolve_async_group_build_handle(batch)
    assert_batch_has_group_build_prefetch_or_rows(batch)
    if fg_batch_stage(batch) is FgBatchStage.SURFACES_PACKED:
        return batch
    return pack_prepared_force_greats_response_frontier_scoring_surfaces(batch)


def build_prepared_force_greats_response_frontier_group_arrays_on_owner(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierPackedScoringBatch:
    """Build response group rows on the GPU owner and pack scoring surfaces."""
    _prof = profile_events_active()
    _t0 = time.perf_counter() if _prof else 0.0
    built = build_prepared_force_greats_response_frontier_group_rows_on_owner(batch)
    if _prof:
        _t_build_done = time.perf_counter()
        emit_profile_event(
            component="fg_fused",
            event="fg_owner_phase",
            metrics={"phase": "build", "total_ms": (_t_build_done - _t0) * 1000.0},
        )
    packed = pack_prepared_force_greats_response_frontier_scoring_surfaces(built)
    if _prof:
        emit_profile_event(
            component="fg_fused",
            event="fg_owner_phase",
            metrics={"phase": "pack", "total_ms": (time.perf_counter() - _t_build_done) * 1000.0},
        )
    return packed


def score_prepared_force_greats_response_frontier_batch_on_gpu_owner(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierOwnerResult:
    """Score a finalized batch on the GPU owner (Taichi kernels only).

    Required hardware-safety boundary: on macOS, ``ti.vulkan`` lowers through MoltenVK, which
    has no ``shaderFloat64``, so the FG inner gem-search kernel compiles at f32 there. f32
    mis-floors the per-note products at score magnitudes (worklog: 129/4M floor mismatches),
    which flips the razor-thin greats-vs-no-greats argmax (FG gains only ~0.4-0.5% over base)
    and makes the search select a greats-free surface -- whose CPU-f64 rescore equals the base
    score, so the FG winner-gate drops every candidate (FG=0). Route the search to the
    bit-exact CPU-f64 owner (the same f64 algorithm the serving path already uses on this Mac).
    """
    if sys.platform == "darwin":
        return score_prepared_force_greats_response_frontier_batch_on_cpu_owner(batch)
    if fg_batch_stage(batch) is not FgBatchStage.SURFACES_PACKED:
        raise RuntimeError(
            "FG response frontier GPU owner score requires a finalized batch "
            "(group rows built and scoring surfaces packed before submit)"
        )
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
    return FgResponseFrontierOwnerResult(
        batch=batch,
        inner_rows=np.asarray(inner_rows, dtype=np.int32),
    )


def score_prepared_force_greats_response_frontier_batch_on_cpu_owner(
    batch: FgResponseFrontierPackedScoringBatch,
) -> FgResponseFrontierOwnerResult:
    """Score a finalized batch with native CPU f64 (no GPU). Same exact algorithm and
    arithmetic as the GPU owner, for the gems-fixed (zero_ms / total_budget == 0) on-demand
    serving shape: tiny per-request work where CPU doubles are lower-latency than emulating
    f64 on a GPU and parallelize across cores instead of serializing on the single GPU."""
    if fg_batch_stage(batch) is not FgBatchStage.SURFACES_PACKED:
        raise RuntimeError(
            "FG response frontier CPU owner score requires a finalized batch "
            "(group rows built and scoring surfaces packed before submit)"
        )
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
    inner_rows, _logical_surface_rows = _score_response_group_meta_cpu(
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
        raise ValueError("response frontier exact CPU batch returned the wrong number of group results")
    return FgResponseFrontierOwnerResult(
        batch=batch,
        inner_rows=np.asarray(inner_rows, dtype=np.int32),
    )


def score_prepared_force_greats_response_frontier_batch_cpu_sync(
    batch: FgResponseFrontierPackedScoringBatch,
    *,
    include_forced_counts: bool = False,
) -> list[FgResponseFrontierSolveResult]:
    """Native-f64 CPU twin of ``score_prepared_force_greats_response_frontier_batch_sync``.

    Enumeration (group rows + packed surfaces) is identical to the GPU path; only the inner
    surface scoring runs on CPU doubles. For the gems-fixed (residual_budget == 0) zero_ms
    rebuild this returns bit-identical results to the GPU owner, with no GPU f64 dependency.
    """
    if batch.scoring_surface_words is None:
        batch = build_prepared_force_greats_response_frontier_group_arrays_on_owner(batch)
    owner = score_prepared_force_greats_response_frontier_batch_on_cpu_owner(batch)
    return materialize_prepared_force_greats_response_frontier_batch_results(
        owner.batch,
        owner.inner_rows,
        include_forced_counts=bool(include_forced_counts),
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


def resolve_fused_owner_score_rows_from_batch(
    batch: FgResponseFrontierPackedScoringBatch,
    inner_rows: np.ndarray,
) -> list[FgFusedOwnerScoreRow]:
    """Resolve the per-candidate owner FG score rows for the fused GA->FG handoff.

    This mirrors the winning-row + surface resolution inside
    ``materialize_prepared_force_greats_response_frontier_batch_results`` but stops
    before ``_solve_result_from_row`` (which needs the full BaseStats dict). One
    row per ``batch.candidate_slices`` entry, in batch order. The caller keys these
    by the batch's ``base_components`` rows (aligned 1:1 with candidate_slices).
    """
    surface_words = batch.scoring_surface_words
    surface_counts = batch.scoring_surface_counts
    group_offsets = batch.scoring_group_offsets
    inner_rows = np.asarray(inner_rows, dtype=np.int32)
    if int(inner_rows.shape[0]) != int(batch.group_meta.shape[0]):
        raise ValueError("response frontier exact GPU batch returned the wrong number of group results")
    out: list[FgFusedOwnerScoreRow] = []
    for _candidate_idx, (start, count) in enumerate(batch.candidate_slices):
        if int(count) <= 0:
            raise ValueError("response frontier exact GPU batch produced no pair result")
        local_idx = int(np.argmax(inner_rows[int(start) : int(start) + int(count), 0]))
        row_idx = int(start) + int(local_idx)
        ft = int(batch.group_ft[row_idx])
        ff = int(batch.group_ff[row_idx])
        ft_stat = int(batch.group_ft_stat[row_idx])
        ff_stat = int(batch.group_ff_stat[row_idx])
        result_row = np.asarray(inner_rows[int(row_idx)], dtype=np.int32).copy()
        result_surface_idx = int(group_offsets[int(row_idx)]) + int(result_row[1])
        result_surface = _surface_from_packed_arrays(
            surface_words=surface_words,
            surface_counts=surface_counts,
            surface_idx=int(result_surface_idx),
        )
        out.append(
            FgFusedOwnerScoreRow(
                ft=int(ft),
                ff=int(ff),
                ft_stat=int(ft_stat),
                ff_stat=int(ff_stat),
                inner_row=tuple(int(v) for v in result_row.tolist()),
                surface=(
                    int(result_surface.fever0),
                    int(result_surface.fever1),
                    int(result_surface.fever2),
                    int(result_surface.fever3),
                    int(result_surface.great0),
                    int(result_surface.great1),
                    int(result_surface.great2),
                    int(result_surface.great3),
                    int(result_surface.body_fever),
                    int(result_surface.body_great),
                    int(result_surface.body_fever_great),
                ),
            )
        )
    return out


def score_fused_owner_base_components_on_gpu_owner(
    *,
    base_components: np.ndarray,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_color: str,
    scoring_bundle: FgResponseFrontierScoringBundle,
    total_budget: int = TOTAL_GEM_BUDGET,
) -> dict[tuple[int, ...], FgFusedOwnerScoreRow]:
    """Score FG response frontier for a candidate set on the GPU owner, fused.

    The fused GA->FG handoff calls this on the owner thread immediately after the
    GA pack/select, with ``base_components`` sliced from the selected payload rows'
    device ``base_stats7`` (Slice 2). It builds the group rows + packs scoring
    surfaces + runs the inner solve, all on the owner (Taichi only), and returns a
    map ``base_components_7tuple -> FgFusedOwnerScoreRow``.

    Rows are deduped by the exact base_components 7-tuple (the minimal scoring set;
    equal base_components => identical FG result). The driver re-derives the same
    7-tuples from the same device base_stats7 and looks up each plan candidate's
    scored row, then materializes with the full BaseStats dict on the host. The
    SCORE here is bit-exact equal to the pre-fusion driver SCORE (a pure function of
    base_components; proven in tests/test_gpu_base_stats7_equivalence.py and the
    Slice 3 fused-path GPU test).

    ``selected_color`` is the song-level selected element (one batch). All other
    FG inputs are song-level (prepared pre-GA via the scoring bundle).
    """
    base_components = np.ascontiguousarray(np.asarray(base_components, dtype=np.int32))
    if int(base_components.ndim) != 2 or int(base_components.shape[1]) != 7:
        raise ValueError("fused owner FG score requires a (N,7) base_components array")
    if int(base_components.shape[0]) <= 0:
        return {}

    # Dedup by the exact 7-tuple -> the minimal scoring set. The first occurrence's
    # tuple keys the result; duplicates resolve to the same row (identical score).
    unique_rows: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    for row in base_components.tolist():
        key = tuple(int(v) for v in row)
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(key)

    batch = prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=[
            {
                "Perfect Points": int(row[0]),
                "Combo Multiplier": int(row[1]),
                "Fever Multiplier": int(row[2]),
                # primary/secondary handled via base_stats7 below, so these dict
                # values are placeholders only; base_stats7 is the authoritative
                # source and overrides them in response_frontier_base_components_row.
                "Fever Time": int(row[5]),
                "Fever Fill Rate": int(row[6]),
            }
            for row in unique_rows
        ],
        base_stats7_list=[tuple(int(v) for v in row) for row in unique_rows],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=str(selected_color or ""),
        total_budget=int(total_budget),
        scoring_bundle=scoring_bundle,
    )
    built = build_prepared_force_greats_response_frontier_group_arrays_on_owner(batch)
    _prof_sc = profile_events_active()
    _t_score = time.perf_counter() if _prof_sc else 0.0
    owner = score_prepared_force_greats_response_frontier_batch_on_gpu_owner(built)
    if _prof_sc:
        _t_score_done = time.perf_counter()
        emit_profile_event(
            component="fg_fused",
            event="fg_owner_phase",
            metrics={"phase": "score_total", "total_ms": (_t_score_done - _t_score) * 1000.0},
        )
    score_rows = resolve_fused_owner_score_rows_from_batch(owner.batch, owner.inner_rows)
    if _prof_sc:
        emit_profile_event(
            component="fg_fused",
            event="fg_owner_phase",
            metrics={"phase": "resolve", "total_ms": (time.perf_counter() - _t_score_done) * 1000.0},
        )
    if len(score_rows) != len(unique_rows):
        raise ValueError(
            "fused owner FG score produced a different row count than the deduped "
            f"base_components set ({len(score_rows)} != {len(unique_rows)})"
        )
    return {key: row for key, row in zip(unique_rows, score_rows, strict=True)}


def build_fused_owner_solve_result_from_score_row(
    *,
    score_row: FgFusedOwnerScoreRow,
    base_stats: dict[str, Any],
    selected_color: str,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    scoring_bundle: FgResponseFrontierScoringBundle,
    started: float | None = None,
    include_forced_counts: bool = False,
) -> FgResponseFrontierSolveResult:
    """Materialize the final FG solve result for one candidate from the owner row.

    Driver-side (full-dict-dependent) half of the fused GA->FG handoff: the GPU
    owner already produced the scored ``score_row`` (inner result + winning surface)
    for this candidate's base_components; here we recombine it with the candidate's
    full ``base_stats`` dict (decode output, all 10 keys) to produce the same
    ``FgResponseFrontierSolveResult`` the pre-fusion SCORE path returned. No GPU.

    The frontier is reconstructed from ``(ft_stat, ff_stat)`` + the song-level
    scoring bundle, exactly as ``materialize_prepared_force_greats_response_frontier
    _batch_results`` does for the SCORE-request path.
    """
    frontier = frontier_result_from_scoring_bundle_for_stats(
        calc_song,
        ref_arrays,
        scoring_bundle,
        ft_stat=int(score_row.ft_stat),
        ff_stat=int(score_row.ff_stat),
    )
    surface = FgResponseSurface(*(int(v) for v in score_row.surface))
    song_inputs = extract_fg_song_inputs(calc_song)
    pair: _ResponsePair = (
        int(score_row.ft),
        int(score_row.ff),
        frontier,
        float(scoring_bundle.raw_fill_by_ff[int(score_row.ff_stat)]),
        float(scoring_bundle.real_time_by_ft[int(score_row.ft_stat)]),
    )
    return _solve_result_from_row(
        started=float(time.perf_counter() if started is None else started),
        base_stats=base_stats,
        selected_color=str(selected_color or ""),
        song_inputs=song_inputs,
        pair=pair,
        row=tuple(int(v) for v in score_row.inner_row),
        surface=surface,
        include_forced_counts=bool(include_forced_counts),
    )


def score_prepared_force_greats_response_frontier_batch_sync(
    batch: FgResponseFrontierPackedScoringBatch,
    *,
    include_forced_counts: bool = False,
) -> list[FgResponseFrontierSolveResult]:
    if batch.scoring_surface_words is None:
        batch = build_prepared_force_greats_response_frontier_group_arrays_on_owner(batch)
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
