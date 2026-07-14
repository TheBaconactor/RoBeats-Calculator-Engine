"""
Shared FT/FF gem-pair enumeration.

skyline owns the GPU-resident FT/FF combo table, and FG should use the same
triangular order when it needs host-visible pair windows. Keeping this contract
small and central prevents skyline/FG search surfaces from drifting.
"""

from __future__ import annotations

import logging
from functools import lru_cache
import numpy as np


logger = logging.getLogger(__name__)


def _normalize_budget(total_budget: int) -> int:
    try:
        budget = int(total_budget)
    except Exception as e:
        logger.debug(f"ftff_combos:_normalize_budget: {e}")
        budget = 0
    return max(0, budget)


def _normalize_cap(value: int | None, total_budget: int) -> int:
    if value is None:
        return int(total_budget)
    try:
        cap = int(value)
    except Exception as e:
        logger.debug(f"ftff_combos:_normalize_cap: {e}")
        cap = int(total_budget)
    return max(0, min(int(total_budget), int(cap)))


@lru_cache(maxsize=64)
def _ftff_combo_arrays_cached(total_budget: int, cap_ft: int, cap_ff: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dim = int(total_budget) + 1
    tri_i, tri_j = np.triu_indices(dim)
    ft = tri_i.astype(np.int32, copy=False)
    ff = (tri_j - tri_i).astype(np.int32, copy=False)
    if int(cap_ft) < int(total_budget) or int(cap_ff) < int(total_budget):
        valid = (ft <= int(cap_ft)) & (ff <= int(cap_ff))
        ft = np.ascontiguousarray(ft[valid], dtype=np.int32)
        ff = np.ascontiguousarray(ff[valid], dtype=np.int32)
    else:
        ft = np.ascontiguousarray(ft, dtype=np.int32)
        ff = np.ascontiguousarray(ff, dtype=np.int32)
    budget_left = (int(total_budget) - ft - ff).astype(np.int32, copy=False)
    ft.setflags(write=False)
    ff.setflags(write=False)
    budget_left.setflags(write=False)
    return ft, ff, budget_left


def ftff_combo_arrays(
    total_budget: int,
    *,
    max_ft_gems: int | None = None,
    max_ff_gems: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Return FT, FF, and remaining-budget arrays in skyline combo-table order.

    Order:
      ft=0,ff=0..B ; ft=1,ff=0..B-1 ; ... ; ft=B,ff=0
    """

    budget = _normalize_budget(total_budget)
    cap_ft = _normalize_cap(max_ft_gems, budget)
    cap_ff = _normalize_cap(max_ff_gems, budget)
    return _ftff_combo_arrays_cached(int(budget), int(cap_ft), int(cap_ff))


__all__ = ["ftff_combo_arrays"]
