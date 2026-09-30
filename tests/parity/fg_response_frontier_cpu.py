"""CPU and GPU parity references for FG response-frontier tests.

``optimize_response_frontier_inner_exact_gpu`` is the per-surface-group GPU inner solve (production scores whole
batches through response_inner_host's group meta scorers on the same kernel).
"""

from typing import Any

import numpy as np
import taichi as ti

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.solver.taichi_gem import api as gem_api
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
    reconstruct_force_greats_response_counts,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import (
    _color_flags,
    _precompute_surface_head_coeffs,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_inner_kernels import (
    SOLVER_NP_FP,
    _fg_response_inner_group_kernel,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_pp_bounds import build_pp_prefix_bounds
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseInnerResult, FgResponseSurface

__all__ = [
    "optimize_response_frontier_inner_exact_gpu",
    "reconstruct_force_greats_response_counts",
]


def _validate_surface(surface: FgResponseSurface, *, body_total: int) -> None:
    if int(surface.body_fever) < 0 or int(surface.body_great) < 0 or int(surface.body_fever_great) < 0:
        raise ValueError("FG response surface body counts must be nonnegative")
    if int(surface.body_fever) > int(body_total) or int(surface.body_great) > int(body_total):
        raise ValueError("FG response surface body count exceeds song body note count")
    if int(surface.body_fever_great) > int(surface.body_fever) or int(surface.body_fever_great) > int(surface.body_great):
        raise ValueError("FG response surface body Fever-Great count exceeds its parent counts")
    if int(surface.body_fever) + int(surface.body_great) - int(surface.body_fever_great) > int(body_total):
        raise ValueError("FG response surface body categories exceed song body note count")


def optimize_response_frontier_inner_exact_gpu(
    surfaces: tuple[FgResponseSurface, ...] | list[FgResponseSurface],
    *,
    total_notes: int,
    residual_budget: int,
    stats_after_ftff: dict[str, Any],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    curves: StatCurves,
) -> FgResponseInnerResult:
    result, _rows = _optimize_response_surfaces_gpu(
        [(int(residual_budget), stats_after_ftff, tuple(surfaces or ()))],
        total_notes=int(total_notes),
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        selected_color=str(selected_color or ""),
        curves=curves,
    )
    if not result:
        raise ValueError("response frontier GPU inner solve requires at least one surface")
    row = result[0]
    return FgResponseInnerResult(
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


def _inner_stat_values_for_colors(
    stats_after_ftff: dict[str, Any] | tuple[int, ...],
    *,
    primary_color: str,
    secondary_color: str,
) -> tuple[int, int, int, int, int]:
    if isinstance(stats_after_ftff, tuple):
        return (
            int(stats_after_ftff[0]),
            int(stats_after_ftff[1]),
            int(stats_after_ftff[2]),
            int(stats_after_ftff[3]),
            int(stats_after_ftff[4]),
        )
    return (
        int(stats_after_ftff.get("Perfect Points", 0) or 0),
        int(stats_after_ftff.get("Combo Multiplier", 0) or 0),
        int(stats_after_ftff.get("Fever Multiplier", 0) or 0),
        int(stats_after_ftff.get(str(primary_color or ""), 0) or 0),
        int(stats_after_ftff.get(str(secondary_color or ""), 0) or 0),
    )


def _optimize_response_surfaces_gpu(
    groups: list[tuple[int, dict[str, Any] | tuple[int, ...], tuple[FgResponseSurface, ...]]],
    *,
    total_notes: int,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    curves: StatCurves,
) -> tuple[list[tuple[int, int, int, int, int, int, int, int, int, int, int]], int]:
    head_len = min(int(total_notes), 100)
    body_total = max(0, int(total_notes) - 100)
    surface_cache: dict[int, tuple[int, int]] = {}
    surface_word_blocks: list[np.ndarray] = []
    surface_count_blocks: list[np.ndarray] = []
    group_meta = np.zeros((len(groups), 8), dtype=np.int32)
    group_offsets = np.zeros(len(groups), dtype=np.int32)
    group_lengths = np.zeros(len(groups), dtype=np.int32)
    logical_surface_rows = 0
    unique_surface_rows = 0

    def _surface_block(surfaces: tuple[FgResponseSurface, ...]) -> tuple[int, int]:
        nonlocal unique_surface_rows
        key = id(surfaces)
        cached = surface_cache.get(key)
        if cached is not None:
            return cached
        words = np.empty((len(surfaces), 8), dtype=np.uint32)
        counts = np.empty((len(surfaces), 3), dtype=np.int32)
        for idx, surface in enumerate(surfaces):
            _validate_surface(surface, body_total=int(body_total))
            words[idx, 0] = int(surface.fever0)
            words[idx, 1] = int(surface.fever1)
            words[idx, 2] = int(surface.fever2)
            words[idx, 3] = int(surface.fever3)
            words[idx, 4] = int(surface.great0)
            words[idx, 5] = int(surface.great1)
            words[idx, 6] = int(surface.great2)
            words[idx, 7] = int(surface.great3)
            counts[idx, 0] = int(surface.body_fever)
            counts[idx, 1] = int(surface.body_great)
            counts[idx, 2] = int(surface.body_fever_great)
        cached = (int(unique_surface_rows), int(words.shape[0]))
        surface_cache[key] = cached
        surface_word_blocks.append(words)
        surface_count_blocks.append(counts)
        unique_surface_rows += int(words.shape[0])
        return cached

    for group_idx, (residual_budget, stats_after_ftff, surfaces) in enumerate(groups):
        cur_pp, cur_cm, cur_fm, cur_primary, cur_secondary = _inner_stat_values_for_colors(
            stats_after_ftff,
            primary_color=str(primary_color or ""),
            secondary_color=str(secondary_color or ""),
        )
        surfaces_tuple = tuple(surfaces or ())
        if not surfaces_tuple:
            continue
        offset, length = _surface_block(surfaces_tuple)
        logical_surface_rows += int(length)
        group_offsets[group_idx] = int(offset)
        group_lengths[group_idx] = int(length)
        group_meta[group_idx] = (
            max(0, int(residual_budget)),
            int(cur_pp),
            int(cur_cm),
            int(cur_fm),
            int(cur_primary),
            int(cur_secondary),
            int(head_len),
            int(body_total),
        )
    if logical_surface_rows <= 0:
        return [], 0

    gem_api.ensure_ready()
    if unique_surface_rows <= 0:
        raise ValueError("response frontier GPU inner solve has groups but no packed surfaces")
    surface_words = np.ascontiguousarray(np.concatenate(surface_word_blocks, axis=0))
    surface_counts = np.ascontiguousarray(np.concatenate(surface_count_blocks, axis=0))
    surface_pattern_words, surface_pattern_ids = np.unique(
        surface_words,
        axis=0,
        return_inverse=True,
    )
    surface_pattern_words = np.ascontiguousarray(surface_pattern_words, dtype=np.uint32)
    surface_pattern_ids = np.ascontiguousarray(surface_pattern_ids, dtype=np.int32)
    surface_pattern_head_coeffs = _precompute_surface_head_coeffs(
        surface_pattern_words,
        head_len=int(head_len),
    )

    flags_tuple = _color_flags(primary_color, secondary_color, selected_color)
    allow_pp = bool(int(flags_tuple[0]) != 0 or int(flags_tuple[1]) != 0)
    flags = np.ascontiguousarray(np.asarray(flags_tuple, dtype=np.int32))
    ref_pp = np.ascontiguousarray(np.asarray(curves.f64["Perfect Points"], dtype=SOLVER_NP_FP))
    ref_cm = np.ascontiguousarray(np.asarray(curves.f64["Combo Multiplier"], dtype=SOLVER_NP_FP))
    ref_fm = np.ascontiguousarray(np.asarray(curves.f64["Fever Multiplier"], dtype=SOLVER_NP_FP))
    pp_prefix_bounds, pp_bound_rows = build_pp_prefix_bounds(group_meta[:, 1], ref_pp, flags)
    out_rows = np.zeros((len(groups), 11), dtype=np.int32)
    _fg_response_inner_group_kernel(
        int(len(groups)),
        surface_pattern_ids,
        surface_pattern_words,
        surface_counts,
        surface_pattern_head_coeffs,
        group_offsets,
        group_lengths,
        group_meta,
        flags,
        ref_pp,
        ref_cm,
        ref_fm,
        pp_prefix_bounds,
        pp_bound_rows,
        out_rows,
        bool(allow_pp),
    )
    ti.sync()

    best_by_group: list[tuple[int, int, int, int, int, int, int, int, int, int, int] | None] = [None] * len(groups)
    for group_idx in range(len(groups)):
        if int(group_lengths[group_idx]) <= 0:
            continue
        raw = out_rows[group_idx]
        candidate = (
            int(raw[0]),
            int(raw[1]),
            int(raw[2]),
            int(raw[3]),
            int(raw[4]),
            int(raw[5]),
            int(raw[6]),
            int(raw[7]),
            int(raw[8]),
            int(raw[9]),
            int(raw[10]),
        )
        best_by_group[int(group_idx)] = candidate
    return [row for row in best_by_group if row is not None], int(logical_surface_rows)
