"""The FG search's floors cut work, not results: on a synthetic score landscape the floored beam search ends with the
same beam (and best loadout) as the same search scoring every neighbour exactly. (A floor makes a neighbour cheaper
inside the gem search; the fake scorer here reports a value below the floor as the kernel does.)"""

from types import SimpleNamespace

import numpy as np

from gear_optimizer.solver.fg_search import search_fg_loadouts

_SLOT_START = np.asarray([0, 5, 10, 15, 20, 25, 30, 30, 30], dtype=np.int32)
_SLOT_COUNT = np.asarray([5, 5, 5, 5, 5, 5, 8, 8, 8], dtype=np.int32)


def _landscape(seed: int):
    rng = np.random.default_rng(seed)
    item_totals = rng.integers(0, 40, size=(38, 7))
    weights = rng.normal(size=7)

    def totals(genomes: np.ndarray) -> np.ndarray:
        return item_totals[genomes].sum(axis=1)

    def score(rows: np.ndarray, floors: np.ndarray) -> dict:
        out = {}
        for row, floor in zip(rows.tolist(), floors.tolist(), strict=True):
            value = int(1000 * np.sin(np.dot(weights, row) / 40.0) + 3 * row[0])  # rugged, many local optima
            out[tuple(row)] = SimpleNamespace(inner_row=(value if value >= floor else floor - 1,))
        return out

    # Four seed loadouts: one random item per gear slot, minis 30-32.
    gear = np.stack([rng.integers(start, start + 5, size=4) for start in range(0, 30, 5)], axis=1)
    seeds = np.concatenate([gear, np.tile([30, 31, 32], (4, 1))], axis=1)
    seed_rows = score(np.asarray(totals(seeds), dtype=np.int64), np.full(4, -(10**9)))
    return seeds, seed_rows, totals, score


def _search(seed: int, floored: bool, beam_width: int):
    seeds, seed_rows, totals, score = _landscape(seed)
    exact = score if floored else (lambda rows, floors: score(rows, np.full(len(rows), -(10**9))))
    found = search_fg_loadouts(seeds=seeds, seed_rows=seed_rows, totals=totals, score=exact, slot_start=_SLOT_START,
                               slot_count=_SLOT_COUNT, beam_width=beam_width)
    ranked = sorted(found, key=lambda k: -found[k][1].inner_row[0])[:beam_width]
    return [(k, found[k][1].inner_row[0]) for k in ranked]


def test_floors_change_no_beam():
    for seed in range(6):
        for beam_width in (1, 2, 4):
            assert _search(seed, True, beam_width) == _search(seed, False, beam_width)
