"""
Shared FT/FF gem-pair enumeration.

GA owns the GPU-resident FT/FF combo table, and FG should use the same
triangular order when it needs host-visible pair windows. Keeping this contract
small and central prevents GA/FG search surfaces from drifting.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any
import logging

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
    Return FT, FF, and remaining-budget arrays in GA combo-table order.

    Order:
      ft=0,ff=0..B ; ft=1,ff=0..B-1 ; ... ; ft=B,ff=0
    """

    budget = _normalize_budget(total_budget)
    cap_ft = _normalize_cap(max_ft_gems, budget)
    cap_ff = _normalize_cap(max_ff_gems, budget)
    return _ftff_combo_arrays_cached(int(budget), int(cap_ft), int(cap_ff))


@lru_cache(maxsize=64)
def _ftff_combo_pairs_array_cached(total_budget: int, cap_ft: int, cap_ff: int) -> np.ndarray:
    ft, ff, _budget_left = _ftff_combo_arrays_cached(int(total_budget), int(cap_ft), int(cap_ff))
    pairs = np.column_stack((ft, ff)).astype(np.int32, copy=False)
    pairs = np.ascontiguousarray(pairs, dtype=np.int32)
    pairs.setflags(write=False)
    return pairs


def ftff_combo_pairs_array(
    total_budget: int,
    *,
    max_ft_gems: int | None = None,
    max_ff_gems: int | None = None,
) -> np.ndarray:
    """Return a read-only ``(n, 2)`` FT/FF pair array in GA combo-table order."""

    budget = _normalize_budget(total_budget)
    cap_ft = _normalize_cap(max_ft_gems, budget)
    cap_ff = _normalize_cap(max_ff_gems, budget)
    return _ftff_combo_pairs_array_cached(int(budget), int(cap_ft), int(cap_ff))


@lru_cache(maxsize=64)
def _ftff_combo_pairs_tuple_cached(total_budget: int, cap_ft: int, cap_ff: int) -> tuple[tuple[int, int], ...]:
    pairs = _ftff_combo_pairs_array_cached(int(total_budget), int(cap_ft), int(cap_ff))
    return tuple((int(row[0]), int(row[1])) for row in pairs)


def ftff_combo_pairs_list(
    total_budget: int,
    *,
    max_ft_gems: int | None = None,
    max_ff_gems: int | None = None,
) -> list[tuple[int, int]]:
    """Return FT/FF pairs as a mutable list while preserving GA combo-table order."""

    budget = _normalize_budget(total_budget)
    cap_ft = _normalize_cap(max_ft_gems, budget)
    cap_ff = _normalize_cap(max_ff_gems, budget)
    return list(_ftff_combo_pairs_tuple_cached(int(budget), int(cap_ft), int(cap_ff)))


@lru_cache(maxsize=32)
def _valid_ftff_mask(total_budget: int) -> np.ndarray:
    b = int(total_budget)
    ft_idx = np.arange(b + 1, dtype=np.int16)[:, None]
    ff_idx = np.arange(b + 1, dtype=np.int16)[None, :]
    valid = (ft_idx + ff_idx) <= b
    valid.setflags(write=False)
    return valid


def collect_ftff_pairs_from_centers(
    centers: Any,
    *,
    search_radius: int,
    total_budget: int,
    use_fast: bool = True,
) -> list[tuple[int, int]]:
    """
    Collect unique FT/FF pairs for an FG search window in GA combo-table order.

    Full-window FG returns the exact same pair order as GA's resident combo table.
    Radius-limited windows remain lexicographic, matching the historical FG
    collector and preserving task/config indexing.
    """

    budget = _normalize_budget(total_budget)
    try:
        radius = int(search_radius)
    except Exception as e:
        logger.debug(f"ftff_combos:collect_ftff_pairs_from_centers: {e}")
        radius = -1

    if radius < 0 or radius >= budget:
        return ftff_combo_pairs_list(budget)

    try:
        if not centers:
            return []
    except Exception as e:
        logger.debug(f"ftff_combos:collect_ftff_pairs_from_centers: {e}")

    if not use_fast:
        needed_pairs_set: set[tuple[int, int]] = set()
        for center_ft, center_ff in centers:
            cft = int(center_ft)
            cff = int(center_ff)
            for ft_offset in range(-radius, radius + 1):
                ft = cft + ft_offset
                if ft < 0 or ft > budget:
                    continue
                for ff_offset in range(-radius, radius + 1):
                    ff = cff + ff_offset
                    if ff < 0 or ft + ff > budget:
                        continue
                    needed_pairs_set.add((ft, ff))
        return sorted(needed_pairs_set)

    b = int(budget)
    mask = np.zeros((b + 1, b + 1), dtype=np.bool_)
    for center_ft, center_ff in centers:
        try:
            cft = int(center_ft)
            cff = int(center_ff)
        except Exception as e:
            logger.debug(f"ftff_combos:collect_ftff_pairs_from_centers: {e}")
            continue
        cft = max(0, min(b, cft))
        cff = max(0, min(b, cff))
        ft_lo = max(0, cft - radius)
        ft_hi = min(b, cft + radius)
        ff_lo = max(0, cff - radius)
        ff_hi = min(b, cff + radius)
        mask[ft_lo : ft_hi + 1, ff_lo : ff_hi + 1] = True

    mask &= _valid_ftff_mask(b)
    pairs = np.argwhere(mask)
    return [(int(ft), int(ff)) for ft, ff in pairs]


__all__ = [
    "collect_ftff_pairs_from_centers",
    "ftff_combo_arrays",
    "ftff_combo_pairs_array",
    "ftff_combo_pairs_list",
]
