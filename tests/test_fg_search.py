"""The FG search's floors and dominance skips cut work, not results: on a synthetic score landscape that, like the FG
score, is non-decreasing in PP, CM, FM and the two colors at fixed FT and FF, the search ends with the same beam (and
best loadout) as the plain beam search that scores every neighbour exactly. (A floor makes a neighbour cheaper inside
the gem search; the fake scorer here reports a value below the floor as the kernel does.)"""

from types import SimpleNamespace

import numpy as np

from gear_optimizer.solver.fg_search import search_fg_loadouts
from gear_optimizer.solver.genetic_pipeline import one_swap_neighborhood

_SLOT_START = np.asarray([0, 5, 10, 15, 20, 25, 30, 30, 30], dtype=np.int32)
_SLOT_COUNT = np.asarray([5, 5, 5, 5, 5, 5, 8, 8, 8], dtype=np.int32)


def _landscape(seed: int, sign: float = 1.0):
    rng = np.random.default_rng(seed)
    item_totals = rng.integers(0, 40, size=(38, 7))
    item_totals[:, 5:] = rng.integers(0, 3, size=(38, 2)) * 10  # few FT / FF totals: many loadouts share them
    weights = sign * rng.uniform(0.0, 3.0, size=5)

    def totals(genomes: np.ndarray) -> np.ndarray:
        return item_totals[genomes].sum(axis=1)

    def score(rows: np.ndarray, floors: np.ndarray) -> dict:
        out = {}
        for row, floor in zip(rows.tolist(), floors.tolist(), strict=True):
            # Rugged across FT / FF (many local optima), monotone in the other totals.
            value = int(np.dot(weights, row[:5]) + 1000 * np.sin((7 * row[5] + 3 * row[6]) / 40.0) + 2000)
            if value >= floor:
                out[tuple(row)] = SimpleNamespace(inner_row=(value,))
        return out

    # Four seed loadouts: one random item per gear slot, minis 30-32.
    gear = np.stack([rng.integers(start, start + 5, size=4) for start in range(0, 30, 5)], axis=1)
    seeds = np.concatenate([gear, np.tile([30, 31, 32], (4, 1))], axis=1)
    seed_rows = score(np.asarray(totals(seeds), dtype=np.int64), np.full(4, -(10**9)))
    return seeds, seed_rows, totals, score


def _plain_search(seeds, seed_rows, totals, score, beam_width):
    """The beam search without floors or skips: each pass scores every new neighbour of the beam exactly."""
    found = {}
    for genome, key in zip(seeds.tolist(), map(tuple, totals(seeds).tolist())):
        found.setdefault(key, (tuple(genome), seed_rows[key]))

    def best_of(keys):
        return sorted(keys, key=lambda k: -found[k][1].inner_row[0])[:beam_width]

    beam = best_of(found)
    while True:
        hood = np.concatenate(
            [one_swap_neighborhood(np.asarray(found[k][0]), _SLOT_START, _SLOT_COUNT, 9) for k in beam]
        )
        fresh = {}
        for genome, key in zip(hood.tolist(), map(tuple, totals(hood).tolist())):
            if key not in found:
                fresh.setdefault(key, tuple(genome))
        rows = score(np.asarray(list(fresh)), np.full(len(fresh), -(10**9)))
        found.update((key, (genome, rows[key])) for key, genome in fresh.items())
        next_beam = best_of([*beam, *fresh])
        if set(next_beam) == set(beam):
            return found
        beam = next_beam


def _best(found, beam_width):
    return [(k, found[k][1].inner_row[0]) for k in sorted(found, key=lambda k: -found[k][1].inner_row[0])[:beam_width]]


def _both(seed: int, beam_width: int, sign: float = 1.0):
    seeds, seed_rows, totals, score = _landscape(seed, sign)
    found = search_fg_loadouts(seeds=seeds, seed_rows=seed_rows, totals=totals, score=score, slot_start=_SLOT_START,
                               slot_count=_SLOT_COUNT, beam_width=beam_width)
    return _best(found, beam_width), _best(_plain_search(seeds, seed_rows, totals, score, beam_width), beam_width)


def test_floors_and_dominance_skips_change_no_beam():
    for seed in range(6):
        for beam_width in (1, 2, 4):
            fast, plain = _both(seed, beam_width)
            assert fast == plain
