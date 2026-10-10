"""
Fever Solver - each loadout's best Base gem allocation, exactly.

A pre-gem stat row is the song's fixed stats plus the loadout's gear/mini item stats; its gems are the full gem budget
(FT/FF/PP/CM/FM/element). Base scoring is Force Greats scoring without Greats, so the song's base timing frontier (each
(Fever Time, Fever Fill) cell's surfaces) is searched by the FG gem search (response_gem_search, CPU float64): every
FT/FF split, every surface of its cell and every PP/CM/FM/element split of the remaining gems, skipping only what a
bound proves cannot win.
"""

from dataclasses import dataclass

import numpy as np

from ...gamedata import Stats, StatCurves
from ...rules import GEM_BUDGET, MAX_STAT
from ...stats import GEM_KINDS, apply_gems
from ..base_stats import build_stats_dict, build_stats_list
from ..force_greats_common import response_frontier_base_components_row
from ..gem_search import SurfacePool, gem_groups, gem_winners
from ..taichi_gem.api.timeline import build_or_load_timeline_frontier_payload
from ..timing_envelope import TimedSong


@dataclass(frozen=True)
class GemSolve:
    """A loadout's best base gem allocation: the gem counts per GEM_KINDS, the stats with those gems, and their
    exact score at the song's timing."""

    gems: tuple[int, ...]
    stats: Stats
    score: int


def solve_best_fever_combination_batch(
    stats_list, song: TimedSong, curves: StatCurves, *, selected_color: str
) -> list[GemSolve]:
    """Each pre-gem stat row's best gem allocation, one GemSolve per row in order; a tie goes to the search's first
    FT/FF split, then its first surface, then the fewest CM, FM and PP gems."""
    rows = [build_stats_dict(build_stats_list(s)) for s in stats_list]
    if not rows:
        return []
    chart = song.chart
    components = np.asarray(
        [
            response_frontier_base_components_row(
                row, None, primary_color=chart.primary, secondary_color=chart.secondary
            )
            for row in rows
        ],
        dtype=np.int32,
    )
    frontier_idx_by_stat, pool = _base_surface_pool(song, curves)
    groups = gem_groups(
        components,
        primary_color=chart.primary,
        secondary_color=chart.secondary,
        frontier_idx_by_stat=frontier_idx_by_stat,
        total_notes=int(chart.total_notes),
        total_budget=GEM_BUDGET,
    )
    solves = []
    for row, winner in zip(
        rows,
        gem_winners(groups, pool, colors=(chart.primary, chart.secondary, selected_color), curves=curves),
        strict=True,
    ):
        _score, _surface, pp, cm, fm, element = winner.inner_row[:6]
        allocation = (pp, cm, fm, winner.ft, winner.ff, element)
        solves.append(
            GemSolve(allocation, apply_gems(row, dict(zip(GEM_KINDS, allocation)), selected_color), winner.inner_row[0])
        )
    return solves


def _base_surface_pool(song: TimedSong, curves: StatCurves) -> tuple[np.ndarray, SurfacePool]:
    """The song's base timing frontier as the gem search reads it: the frontier of each (Fever Time, Fever Fill) cell
    (one per distinct surface range of the payload) and the surfaces, without Greats."""
    payload = build_or_load_timeline_frontier_payload(song, curves).payload
    used = int(payload.frontier_pool_used)
    cell_ranges = np.stack((payload.grid_frontier_offset[0].ravel(), payload.grid_frontier_count[0].ravel()), axis=1)
    ranges, frontier_idx = np.unique(cell_ranges, axis=0, return_inverse=True)
    heads, first_rows, pattern_ids = np.unique(
        np.asarray(payload.grid_frontier_masks_bits_pool[0, :used, :4], dtype=np.uint32),
        axis=0,
        return_index=True,
        return_inverse=True,
    )
    pattern_words = np.zeros((heads.shape[0], 8), dtype=np.uint32)
    pattern_words[:, :4] = heads
    counts = np.zeros((used, 3), dtype=np.int32)
    counts[:, 0] = payload.grid_frontier_body_fever_pool[0, :used]
    pool = SurfacePool(
        frontier_offsets=ranges[:, 0].astype(np.int32),
        frontier_lengths=ranges[:, 1].astype(np.int32),
        pattern_ids=pattern_ids.reshape(-1).astype(np.int32),
        pattern_words=pattern_words,
        counts=counts,
        head_coeffs=payload.grid_frontier_head_coeffs_pool[0, first_rows, :].astype(np.int32),
    )
    return frontier_idx.reshape(MAX_STAT + 1, MAX_STAT + 1).astype(np.int32), pool
