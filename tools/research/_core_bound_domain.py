"""Song-materialized catalog domain, with no heuristic or skyline filtering."""

from dataclasses import dataclass
from math import comb, prod

import numpy as np

from gear_optimizer.core.constants import TOTAL_GEM_BUDGET
from gear_optimizer.core.utils import _relevant_row_projection
from gear_optimizer.data.mini_ascension import materialize_minis_for_song
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
from gear_optimizer.solver.solver_common import GEAR_SLOTS


def project(item, primary, secondary):
    pp, cm, fm, ft, ff, p, s = _relevant_row_projection(item, primary, secondary)
    return [pp, cm, fm, ft, ff, 2 * p + s]


@dataclass(frozen=True)
class CatalogDomain:
    fixed: np.ndarray
    gear: tuple[np.ndarray, ...]
    minis: np.ndarray
    gems: np.ndarray
    intervals: np.ndarray
    budget: int
    gear_items: tuple
    mini_items: tuple

    @property
    def loadouts(self):
        return prod(len(g) for g in self.gear) * comb(len(self.minis), 3)


def catalog_domain(gears, minis, *, song, fixed, budget=TOTAL_GEM_BUDGET):
    primary = song["metadata"]["Primary Color"]
    secondary = song["metadata"].get("Secondary Color", "")
    materialized, _, _ = materialize_minis_for_song(
        minis, calc_song=song, primary_color=primary, secondary_color=secondary,
    )
    gear_rows = [[g for g in gears if g["type"] == slot] for slot in GEAR_SLOTS]
    if any(not rows for rows in gear_rows) or len(materialized) < 3 or budget < 0:
        raise ValueError("incomplete catalog or invalid gem budget")
    for rows in [*gear_rows, materialized]:
        if len({g["Name"] for g in rows}) != len(rows):
            raise ValueError("catalog witnesses must have distinct names within each pool")
    gear = tuple(np.array([project(g, primary, secondary) for g in rows], dtype=np.int64)
                 for rows in gear_rows)
    mini = np.array([project(m, primary, secondary) for m in materialized], dtype=np.int64)
    base = np.array(project(fixed, primary, secondary), dtype=np.int64)
    # Derive all six gem vectors through the production stat writer, including
    # FT/FF's elemental contribution and the selected-primary overflow gems.
    gems = np.array([project(apply_gems_to_base_stats({}, primary, *allocation), primary, secondary)
                     for allocation in np.eye(6, dtype=np.int64)], dtype=np.int64)
    ordered = np.sort(mini, axis=0)
    lo = base + sum(g.min(axis=0) for g in gear) + ordered[:3].sum(axis=0)
    hi = base + sum(g.max(axis=0) for g in gear) + ordered[-3:].sum(axis=0)
    lo += budget * np.minimum(0, gems.min(axis=0))
    hi += budget * np.maximum(0, gems.max(axis=0))
    return CatalogDomain(base, gear, mini, gems, np.stack([lo, hi], axis=1), budget,
                         tuple(tuple(rows) for rows in gear_rows), tuple(materialized))


def base_fever_counts(payload):
    """Max count over EVERY response surface in each canonical Base FT/FF cell."""
    count = np.asarray(payload.grid_frontier_count)[0]
    offset = np.asarray(payload.grid_frontier_offset)[0]
    body = np.asarray(payload.grid_frontier_body_fever_pool)[0]
    coeff = np.asarray(payload.grid_frontier_head_coeffs_pool)[0]
    # Head coefficients are (normal count, fever count, normal sum, fever sum).
    fever = body.astype(np.int64) + coeff[:, 1]
    if np.any(count <= 0) or np.any(offset < 0) or np.any(offset + count > len(fever)):
        raise ValueError("Base timing coverage must include every lookup cell")
    result = np.zeros(count.shape, dtype=np.int64)
    for ft, ff in np.ndindex(count.shape):
        start = int(offset[ft, ff])
        result[ft, ff] = fever[start:start + int(count[ft, ff])].max()
    return result
