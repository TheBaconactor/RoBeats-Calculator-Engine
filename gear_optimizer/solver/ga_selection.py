"""The loadouts a song's GA hands to the FG stage: the best candidates by Base score, one per effective loadout.

Two loadouts are the same effective loadout when their gears share names and their minis fold to the same signature in
the song's colors (loadout_equivalence), the hash the stored surface dedups by (pipeline.fg._selected_surface), on dense
ids: a gear's name rank and a mini's signature id.
"""

from __future__ import annotations

from typing import Any, NamedTuple

import numpy as np

from gear_optimizer.data.loadout_equivalence import effective_mini_signature
from gear_optimizer.solver.item_registry import MINI_SLOT_INDICES, ItemRegistry


class GaSelection(NamedTuple):
    """The loadouts the GA selected. A loadout's `results` are its Base score and gems: [score, FT, FF, PP, CM, FM,
    element]; its `base_stats` its pre-gem [PP, CM, FM, primary, secondary, FT, FF]."""

    best_score: int
    best_genome: np.ndarray
    best_results: np.ndarray
    scores: np.ndarray
    genomes: np.ndarray
    results: np.ndarray
    base_stats: np.ndarray


def effective_tables(registry: ItemRegistry, primary: str, secondary: str) -> tuple[np.ndarray, np.ndarray]:
    """(gear name rank, mini signature id) by item id: equal iff the items are equivalent in this color context, dense
    and ordered by name / signature; id 0 (the empty slot) keeps 0."""
    mini_start, mini_count = int(registry.slot_start[MINI_SLOT_INDICES[0]]), int(registry.slot_count[MINI_SLOT_INDICES[0]])
    items = registry.id_to_item
    rank, sig_id = np.zeros((2, int(registry.n_items)), dtype=np.int32)
    names = {item_id: items[item_id].name for item_id in range(1, mini_start)}
    rank_of_name = {name: index for index, name in enumerate(sorted(set(names.values())), start=1)}
    for item_id, name in names.items():
        rank[item_id] = rank_of_name[name]
    sigs: dict[int, tuple[Any, ...]] = {
        item_id: effective_mini_signature(items[item_id].stats, primary, secondary, primary)
        for item_id in range(mini_start, mini_start + mini_count)
    }
    id_of_sig = {
        sig: index for index, sig in enumerate(sorted(set(sigs.values()), key=lambda sig: "|".join(map(str, sig))), start=1)
    }
    for item_id, sig in sigs.items():
        sig_id[item_id] = id_of_sig[sig]
    return rank, sig_id


def select_ga_loadouts(table: np.ndarray, gear_rank: np.ndarray, mini_sig: np.ndarray, limit: int) -> GaSelection:
    """The `limit` best of a candidate table (gpu.ga.run_ga: rows [score, ids(9), results(7), base stats(7)], minis
    sorted) by Base score, one row per effective loadout: the row with its highest score, the earliest on a tie. Equal
    scores rank by item ids, descending, then by which loadout the table met first."""
    rows = table.reshape(-1, table.shape[-1])
    rows = rows[rows[:, 0] > 0]
    keys = np.hstack([np.sort(gear_rank[rows[:, 1:7]], axis=1), np.sort(mini_sig[rows[:, 7:10]], axis=1)])
    scores, ids = rows[:, 0].tolist(), (-rows[:, 1:10]).tolist()
    kept: dict[tuple, int] = {}
    for index, key in enumerate(map(tuple, keys.tolist())):
        if key not in kept or scores[index] > scores[kept[key]]:
            kept[key] = index
    order = sorted(enumerate(kept.values()), key=lambda stub: (-scores[stub[1]], ids[stub[1]], stub[0]))
    selected = rows[[index for _stub, index in order[:limit]]]
    best = selected[0]
    return GaSelection(int(best[0]), best[1:10], best[10:17], selected[:, 0], selected[:, 1:10], selected[:, 10:17],
                       selected[:, 17:24])
