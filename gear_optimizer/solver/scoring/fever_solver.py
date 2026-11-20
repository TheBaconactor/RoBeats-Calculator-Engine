"""
Fever Solver - each loadout's best Base gem allocation, exactly.

A pre-gem stat row is the song's fixed stats plus the loadout's gear/mini item stats; its gems are the full gem budget
(FT/FF/PP/CM/FM/element). Base scoring is Force Greats scoring without Greats, so the song's base timing frontier (each
(Fever Time, Fever Fill) cell's surfaces) is searched by the FG gem search (response_gem_search, CPU float64): every
FT/FF split, every surface of its cell and every PP/CM/FM/element split of the remaining gems, skipping only what a
bound proves cannot win.
"""

from dataclasses import dataclass
import threading

import numpy as np

from ...gamedata import Stats, StatCurves
from ...rules import MAX_STAT
from ...stats import GEM_KINDS, apply_gems
from ..base_stats import STAT_NAMES, loadout_totals
from ..gem_search import GemMemo, gem_winners
from gear_optimizer.frontier.cache_scope import frontier_cache_is_ephemeral
from gear_optimizer.frontier.timeline_cache import build_or_load_timeline_frontier_payload
from gear_optimizer.frontier.types import SurfacePool
from ..timing_envelope import TimedSong


_base_pool_local = threading.local()


@dataclass(frozen=True)
class GemSolve:
    """A loadout's best base gem allocation: the gem counts per GEM_KINDS, the stats with those gems, and their
    exact score at the song's timing."""

    gems: tuple[int, ...]
    stats: Stats
    score: int


def solve_best_fever_combination_batch(
    stats_list, song: TimedSong, curves: StatCurves, *, selected_color: str, memo: GemMemo | None = None
) -> list[GemSolve]:
    """Each pre-gem stat row's best gem allocation, one GemSolve per row in order; a tie goes to the search's first
    FT/FF split, then its first surface, then the fewest CM, FM and PP gems."""
    rows = [{name: s[name] for name in STAT_NAMES} for s in stats_list]
    if not rows:
        return []
    chart = song.chart
    totals = [loadout_totals(row, chart.primary, chart.secondary) for row in rows]
    unique_totals = list(dict.fromkeys(totals))
    total_notes = int(chart.total_notes)
    winner_by_total = dict(
        zip(
            unique_totals,
            gem_winners(
                np.asarray(unique_totals, dtype=np.int32),
                _base_surface_pool(song, curves),
                colors=(chart.primary, chart.secondary, selected_color),
                curves=curves,
                notes=(min(total_notes, 100), max(0, total_notes - 100)),
                memo=memo,
            ),
            strict=True,
        )
    )
    solves = []
    for row, key in zip(rows, totals, strict=True):
        winner = winner_by_total[key]
        _score, _surface, pp, cm, fm, element = winner.inner_row
        allocation = (pp, cm, fm, winner.ft, winner.ff, element)
        solves.append(
            GemSolve(allocation, apply_gems(row, dict(zip(GEM_KINDS, allocation)), selected_color), winner.inner_row[0])
        )
    return solves


def _base_surface_pool(song: TimedSong, curves: StatCurves) -> tuple[np.ndarray, SurfacePool]:
    """The song's base timing frontier as the gem search reads it: the frontier of each (Fever Time, Fever Fill) cell
    (one per distinct surface range of the payload) and the surfaces, without Greats. A song's batches share it: the
    timeline cache serves them one payload object."""
    ephemeral = frontier_cache_is_ephemeral()
    payload = build_or_load_timeline_frontier_payload(song, curves).payload
    if not ephemeral:
        last = getattr(_base_pool_local, "last", None)
        if last is not None and last[0] is payload:
            return last[1], last[2]
    used = int(payload.frontier_pool_used)
    packed_ranges = (
        (payload.grid_frontier_offset[0].ravel().astype(np.int64) << 32)
        | payload.grid_frontier_count[0].ravel().astype(np.int64)
    )
    unique_ranges, frontier_idx = np.unique(packed_ranges, return_inverse=True)
    pattern_words = np.zeros((used, 8), dtype=np.uint32)
    pattern_words[:, :4] = payload.grid_frontier_masks_bits_pool[0, :used, :4]
    counts = np.zeros((used, 3), dtype=np.int32)
    counts[:, 0] = payload.grid_frontier_body_fever_pool[0, :used]
    pool = SurfacePool(
        frontier_offsets=(unique_ranges >> 32).astype(np.int32),
        frontier_lengths=(unique_ranges & 0xFFFFFFFF).astype(np.int32),
        pattern_ids=np.arange(used, dtype=np.int32),
        pattern_words=pattern_words,
        counts=counts,
        head_coeffs=payload.grid_frontier_head_coeffs_pool[0, :used, :].astype(np.int32),
        head_greats=np.zeros((used, 2), dtype=np.int32),
    )
    frontier_idx = frontier_idx.reshape(MAX_STAT + 1, MAX_STAT + 1).astype(np.int32)
    if not ephemeral:
        _base_pool_local.last = (payload, frontier_idx, pool)
    return frontier_idx, pool
