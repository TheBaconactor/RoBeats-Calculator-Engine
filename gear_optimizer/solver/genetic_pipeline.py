"""The GA's inputs and policy, and what it computes on the host: the heuristic seed items it starts from and the 1-swap
neighborhood its polish evaluates. The GA itself runs on the GPU (gpu.ga)."""

from dataclasses import dataclass

import numpy as np

from gear_optimizer.gamedata import StatCurves
from gear_optimizer.solver.base_stats import COLOR_TO_STAT_INDEX
from gear_optimizer.solver.ftff_combos import FtffShortlist
from gear_optimizer.solver.timing_envelope import TimedSong

# Runs fall into a song's basins independently, so more, smaller runs reach the best one more often: 5 runs of 352
# (5/6 of the evaluations of the former 3 x 705) missed the best-known Base #1 in 1.5% of default searches on 31
# held-out charts vs 3.8%, with 7-15% less GA time (PLAN.md 10-07).
GA_POPULATION_SIZE = 352
GA_MUTATION_RATE = 0.35
GA_TOURNAMENT_K = 3
GA_NOVELTY_REPAIR_ATTEMPTS = 2
GA_DIVERSE_PARENT_B_RATE = 0.125  # An FG-proxy tournament for parent B: diversity for the FG stage.
GA_INIT_HEURISTIC_K = 64  # The top items per slot that the heuristic-seeded initial genomes draw from.


@dataclass
class GaInputs:
    """What a song's GA needs."""

    timed_song: TimedSong
    curves: StatCurves
    color_flags: dict[str, int]
    gens_per_run: int
    num_runs: int
    n_genomes: int
    item_stats: np.ndarray
    slot_start: np.ndarray
    slot_count: np.ndarray
    base_fixed_stats_arr: np.ndarray
    init_heuristic_topk: np.ndarray
    init_heuristic_copies: int
    ftff_shortlist: FtffShortlist


def build_ga_init_heuristic_topk(
    *,
    item_stats: "np.ndarray",
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    primary_color: str,
    secondary_color: str,
    heuristic_k: int,
) -> "np.ndarray":
    """Per slot, the heuristic_k items with the most 2 x primary + secondary + Perfect Points (lower id first on a tie),
    the last one repeated when the pool is smaller; an empty slot keeps id 0."""
    score_cols = [COLOR_TO_STAT_INDEX[primary_color], COLOR_TO_STAT_INDEX[primary_color],
                  COLOR_TO_STAT_INDEX[secondary_color], 0]
    topk = np.zeros((len(slot_start), heuristic_k), dtype=np.int32)
    for slot_i, (start, count) in enumerate(zip(slot_start, slot_count)):
        if not count:
            continue
        ids = np.arange(start, start + count, dtype=np.int32)
        score = item_stats[ids][:, score_cols].astype(np.int64).sum(axis=1)
        sel = ids[np.lexsort((ids.astype(np.int64), -score))[:heuristic_k]]
        topk[slot_i, : len(sel)] = sel
        topk[slot_i, len(sel) :] = sel[-1]
    return topk


def one_swap_neighborhood(
    incumbent: "np.ndarray",
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    n_slots: int,
) -> "np.ndarray":
    """All single-slot substitutions of `incumbent` (mini uniqueness preserved).

    Gear slots (0-5) swap to every other item in the slot pool; mini slots (6-8)
    additionally exclude the incumbent's other two minis. Returns (K, n_slots) i32.
    """
    inc = np.asarray(incumbent, dtype=np.int64)
    rows = []
    for s in range(n_slots):
        pool = np.arange(slot_start[s], slot_start[s] + slot_count[s], dtype=np.int64)
        pool = pool[pool != inc[s]]
        if s >= 6:
            pool = pool[~np.isin(pool, [inc[j] for j in range(6, n_slots) if j != s])]
        if pool.size == 0:
            continue
        block = np.tile(inc, (pool.size, 1))
        block[:, s] = pool
        rows.append(block)
    if not rows:
        return np.zeros((0, n_slots), dtype=np.int32)
    return np.ascontiguousarray(np.concatenate(rows, axis=0).astype(np.int32))
