"""
Fever Solver - best gem allocation for fixed loadouts, on the canonical GPU registry solve.

- solve_best_fever_combination_batch: N pre-gem stat rows in one GPU dispatch

A pre-gem stat row is the song's fixed stats plus the loadout's gear/mini item stats. The solve
allocates the full FT/FF/PP/CM/FM/Overflow gem budget for the best score.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from ...core.color_flags import build_color_flags

from ..base_stats import build_stats_array, build_stats_dict, build_stats_list
from ..registry_solve_request import RegistrySolveRequest, dispatch_registry_solve

from ..timing_envelope import TimedSong
from ...gamedata import Stats
from ...stats import GEM_KINDS, apply_gems
from .exact_rescore import score_base_exact_batch

def _color_flags(song: TimedSong, selected_color: str) -> dict[str, int]:
    return build_color_flags(song.chart.primary, song.chart.secondary, selected_color)


@dataclass(frozen=True)
class GemSolve:
    """A loadout's best base gem allocation: the gem counts per GEM_KINDS, the stats with those gems, and their
    exact score at the song's timing."""

    gems: tuple[int, ...]
    stats: Stats
    score: int


def solve_best_fever_combination_batch(
    stats_list, song: TimedSong, curves, *, selected_color, song_slot: int = 0
) -> list[GemSolve]:
    """Batched GPU base gem re-solve: N loadouts in ONE skyline dispatch (n_genomes=N).

    The whole base solve (timeline reuse + skyline + scoring) then runs once for all loadouts, and
    the batch warmstart keeps each loadout's combo sweep independent. ``stats_list`` is N pre-gem
    stat rows (song fixed stats + tier delta + gear/mini item stats). Returns one GemSolve per
    input, in order: the search's allocation after ``exact_climb``. Each loadout's gem search is
    independent, so a loadout's result does not depend on the batch."""
    rows = [build_stats_dict(build_stats_list(s)) for s in (stats_list or [])]
    if not rows:
        return []

    n = len(rows)
    # Encode each loadout's pre-gem stats as ONE item in the skyline item pool. The
    # aggregator skips item_id == 0 (empty sentinel), so put loadout g at item g+1 and have
    # population_indices select only that item (slots 1-8 stay 0/empty). base_fixed_stats is 0, so
    # the aggregator yields exactly each loadout's pre-gem stats.
    item_stats = np.zeros((n + 1, 10), dtype=np.int32)
    population_indices = np.zeros((n, 9), dtype=np.int32)
    for g, stats in enumerate(rows):
        item_stats[g + 1, :] = build_stats_array(stats)[:10]
        population_indices[g, 0] = g + 1

    request = RegistrySolveRequest(
        population_indices=population_indices,
        item_stats=item_stats,
        slot_start=np.zeros((9,), dtype=np.int32),
        slot_count=np.zeros((9,), dtype=np.int32),
        base_fixed_stats=np.zeros((10,), dtype=np.int32),
        song=song,
        curves=curves,
        flags=_color_flags(song, selected_color),
        song_slot=int(song_slot),
    )
    gpu_results = dispatch_registry_solve(request)
    if not gpu_results or len(gpu_results) != n:
        raise RuntimeError(
            f"batched base re-solve returned {len(gpu_results) if gpu_results else 0} results for {n} genomes"
        )
    searched = []
    for solved in gpu_results:
        _search_score, ft, ff, g_pp, g_cm, g_fm, g_ov = (int(v) for v in solved)
        searched.append((g_pp, g_cm, g_fm, ft, ff, g_ov))
    allocations, scores = exact_climb(
        rows, searched, selected_color, lambda stats: score_base_exact_batch(stats, song, curves)
    )
    return [
        GemSolve(allocation, apply_gems(stats, dict(zip(GEM_KINDS, allocation)), selected_color), score)
        for stats, allocation, score in zip(rows, allocations, scores, strict=True)
    ]


def exact_climb(
    rows: Sequence[Mapping[str, int]],
    allocations: Sequence[tuple[int, ...]],
    selected_color: str,
    exact_scores: Callable[[list[Stats]], Sequence[int]],
) -> tuple[list[tuple[int, ...]], list[int]]:
    """Each row's allocation (per GEM_KINDS) hill-climbed with the exact scorer from the search's, and its exact score.

    The search ranks allocations in float32 on MoltenVK and can stop one gem move short of the float64 optimum
    (Kanpai (Hard): 66,023,473 where moving one element gem to Fever Fill Rate scores 66,024,847). Each step moves
    one gem between kinds on every row where that strictly improves the exact score (the first best move), scoring
    all rows' moves in one exact batch, until no row improves. ``rows`` are the pre-gem stats."""

    def stats_of(i: int, allocation: tuple[int, ...]) -> Stats:
        return apply_gems(rows[i], dict(zip(GEM_KINDS, allocation)), selected_color)

    current = [tuple(int(g) for g in a) for a in allocations]
    scores = [int(s) for s in exact_scores([stats_of(i, a) for i, a in enumerate(current)])]
    active = range(len(current))
    while active:
        moves = [(i, m) for i in active for m in _one_gem_moves(current[i])]
        best: dict[int, tuple[int, tuple[int, ...]]] = {}
        for (i, m), s in zip(moves, exact_scores([stats_of(i, m) for i, m in moves]), strict=True):
            if s > scores[i] and (i not in best or s > best[i][0]):
                best[i] = (int(s), m)
        for i, (s, m) in best.items():
            scores[i], current[i] = s, m
        active = sorted(best)
    return current, scores


def _one_gem_moves(allocation: tuple[int, ...]) -> list[tuple[int, ...]]:
    """Every allocation one gem away: one gem moved from one kind to another (the budget is unchanged)."""
    moves = []
    for a, count in enumerate(allocation):
        if count:
            for b in range(len(allocation)):
                if b != a:
                    moved = list(allocation)
                    moved[a] -= 1
                    moved[b] += 1
                    moves.append(tuple(moved))
    return moves
