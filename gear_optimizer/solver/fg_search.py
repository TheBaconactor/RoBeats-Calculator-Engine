"""The Force Greats search: a beam search on the exact FG score over 1-swap loadout neighbourhoods.

The GA ranks loadouts by their Base score and FG is scored for the loadouts it selects, but a loadout where forced
Greats pay can rank low on Base. The search starts from those loadouts' FG scores and keeps the beam_width best distinct
pre-gem totals (equal totals score alike). Each pass FG-scores the unscored 1-swap neighbours of the beam, each with the
score that enters the beam as its floor, in chunks between which the floor rises with the beam; a pass that leaves the
beam unchanged ends the search. A neighbour below its floor cannot enter the beam, then or later (the floor never
falls), so the floors cut the gem search's work without changing the beam.

Cost: passes x beam_width x N1 neighbours (N1 = the 1-swap neighbourhood, about 180-250), minus totals already scored
or pruned; a neighbour below its floor costs only the gem search's bound checks (COMPLEXITY.md section 4).
"""

from collections.abc import Callable
from typing import Any

import numpy as np

from .genetic_pipeline import one_swap_neighborhood

_CHUNK = 256  # neighbours per scoring call: the floor rises between calls


def search_fg_loadouts(
    *,
    seeds: np.ndarray,
    seed_rows: dict[tuple[int, ...], Any],
    totals: Callable[[np.ndarray], np.ndarray],
    score: Callable[[np.ndarray, np.ndarray], dict[tuple[int, ...], Any]],
    slot_start: np.ndarray,
    slot_count: np.ndarray,
    beam_width: int,
) -> dict[tuple[int, ...], tuple[tuple[int, ...], Any]]:
    """Every loadout the search scored exactly, by its pre-gem totals: (its first genome, its FG score row).

    seeds: (N, 9) genomes whose totals key their FG score rows in seed_rows. totals: genomes -> their (M, 7) pre-gem
    totals. score: (totals rows, floors) -> each row's FG score row (row.inner_row[0] is exact when it reaches the
    row's floor, else only below it)."""
    found: dict[tuple[int, ...], tuple[tuple[int, ...], Any]] = {}
    for genome, key in zip(seeds.tolist(), map(tuple, totals(seeds).tolist()), strict=True):
        if key not in found:
            found[key] = (tuple(genome), seed_rows[key])
    pruned: set[tuple[int, ...]] = set()

    def best_of(keys):  # the beam_width best, ties kept in order
        return sorted(keys, key=lambda k: -found[k][1].inner_row[0])[:beam_width]

    beam = best_of(found)
    while True:
        hood = np.concatenate(
            [one_swap_neighborhood(np.asarray(found[k][0]), slot_start, slot_count, 9) for k in beam]
        )
        fresh: dict[tuple[int, ...], tuple[int, ...]] = {}
        for genome, key in zip(hood.tolist(), map(tuple, totals(hood).tolist()), strict=True):
            if key not in found and key not in pruned and key not in fresh:
                fresh[key] = tuple(genome)
        contenders = list(beam)
        keys = list(fresh)
        for start in range(0, len(keys), _CHUNK):
            chunk = keys[start : start + _CHUNK]
            top = best_of(contenders)
            floor = found[top[-1]][1].inner_row[0] if len(top) == beam_width else -1
            rows = score(np.asarray(chunk, dtype=np.int32), np.full(len(chunk), floor, dtype=np.int64))
            for key in chunk:
                if rows[key].inner_row[0] >= floor:
                    found[key] = (fresh[key], rows[key])
                    contenders.append(key)
                else:
                    pruned.add(key)
        next_beam = best_of(contenders)
        if set(next_beam) == set(beam):
            return found
        beam = next_beam
