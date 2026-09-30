"""
Fever Solver - best gem allocation for fixed loadouts, on the canonical GPU registry solve.

- solve_best_fever_combination: one pre-gem stat row
- solve_best_fever_combination_batch: N pre-gem stat rows in one GPU dispatch

A pre-gem stat row is the song's fixed stats plus the loadout's gear/mini item stats. The solve
allocates the full FT/FF/PP/CM/FM/Overflow gem budget for the best score.
"""

import numpy as np

from ...core.color_flags import build_color_flags
from ...core.gem_defs import build_gem_counts

from ..base_stats import build_stats_array, build_stats_dict, build_stats_list
from ..registry_solve_request import RegistrySolveRequest, dispatch_registry_solve

from ..timing_envelope import TimedSong
from ...stats import apply_gems, gems

def _color_flags(song: TimedSong, selected_color: str) -> dict[str, int]:
    return build_color_flags(song.chart.primary, song.chart.secondary, selected_color)


def _gem_result(stats: dict[str, int], selected_color: str, solved) -> dict:
    score, ft, ff, g_pp, g_cm, g_fm, g_ov = (int(v) for v in solved)
    final_stats = apply_gems(stats, gems(pp=g_pp, cm=g_cm, fm=g_fm, ft=ft, ff=ff, element=g_ov), selected_color)
    gem_counts = build_gem_counts(g_pp, g_cm, g_fm, g_ov)
    return {
        "Score": score,
        "FT": ft,
        "FF": ff,
        "config": {
            "FT Gems": ft,
            "FF Gems": ff,
            "PP Gems": g_pp,
            "CM Gems": g_cm,
            "FM Gems": g_fm,
            "Overflow Gems": g_ov,
        },
        "FT_gems": ft,
        "FF_gems": ff,
        "gem_counts": gem_counts,
        "GemCounts": gem_counts,
        "Stats": final_stats,
        "Selected Element": selected_color,
    }


def solve_best_fever_combination_batch(stats_list, song: TimedSong, curves, *, selected_color, song_slot: int = 0):
    """Batched GPU base gem re-solve: N loadouts in ONE skyline dispatch (n_genomes=N).

    The whole base solve (timeline reuse + skyline + scoring) then runs once for all loadouts, and
    the batch warmstart keeps each loadout's combo sweep independent. ``stats_list`` is N pre-gem
    stat rows (song fixed stats + tier delta + gear/mini item stats). Returns one result dict
    per input, in order: ``{Score, FT, FF, GemCounts, Stats, Selected Element, config}``. Each
    loadout's gem search is independent, so the per-loadout result is identical to the single-loadout
    ``solve_best_fever_combination`` -- served-batched == native-per-loadout (delta=0)."""
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
    return [_gem_result(stats, selected_color, solved) for stats, solved in zip(rows, gpu_results, strict=True)]
