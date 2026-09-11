"""Exact integer support of the shared gem budget inside a raw timing region."""

import numpy as np

from gear_optimizer.core.constants import GEM_SCALE_FEVER, GEM_SCALE_NORMAL, MAX_STAT_INDEX

# Gem order FT, FF, PP, CM, FM, overflow; projected stat order PP, CM, FM, FT, FF, E.
_AXES = np.array([3, 4, 0, 1, 2])
_SCALES = np.array([GEM_SCALE_FEVER, GEM_SCALE_FEVER, GEM_SCALE_NORMAL,
                    GEM_SCALE_NORMAL, GEM_SCALE_FEVER])


def gem_limits(base, intervals, budget):
    """All legal gem allocations in this region lie within these inclusive limits.

    Raw over-cap bases retain zero-gem allocations; they are not clipped into a
    different region. Overflow absorbs the unused budget in an actual solve.
    """
    base = np.asarray(base, dtype=np.int64)
    low = np.zeros((*base.shape[:-1], 6), dtype=np.int64)
    high = np.full_like(low, budget)
    high[..., :5] = np.minimum(budget, np.maximum(0, (MAX_STAT_INDEX - base[..., _AXES]) // _SCALES))
    for gem, axis in enumerate((3, 4)):
        low[..., gem] = np.maximum(0, -((base[..., axis] - intervals[axis, 0]) // _SCALES[gem]))
        high[..., gem] = np.minimum(high[..., gem], (intervals[axis, 1] - base[..., axis]) // _SCALES[gem])
    feasible = np.all(low <= high, axis=-1) & (low.sum(axis=-1) <= budget)
    return low, high, feasible


def constrained_support(gamma, low, high, budget, order=None):
    """Maximize EACH affine gem objective, not the nonlinear game score.

    Every gem costs one unit. Pay mandatory counts, then fill positive-weight
    capacities in descending order. Inputs must describe a feasible box.
    """
    gamma = np.asarray(gamma, dtype=np.int64)
    order = np.argsort(-gamma, axis=0, kind="stable") if order is None else order
    values = low @ gamma
    remaining = np.repeat((budget - low.sum(axis=1))[:, None], gamma.shape[1], axis=1)
    columns = np.arange(gamma.shape[1])
    for rank in range(6):
        gems = order[rank]
        take = np.minimum(remaining, high[:, gems] - low[:, gems])
        take = np.where(gamma[gems, columns] > 0, take, 0)
        values += take * gamma[gems, columns]
        remaining -= take
    return values


def regional_upper(base, region, gems, budget):
    """Return per-loadout upper logs; infeasible rows use the int64 minimum."""
    base = np.atleast_2d(base)
    low, high, feasible = gem_limits(base, region.intervals, budget)
    result = np.full(len(base), np.iinfo(np.int64).min, dtype=np.int64)
    if np.any(feasible):
        bank = region.bank
        gamma = gems @ bank.weights.T
        support = constrained_support(gamma, low[feasible], high[feasible], budget)
        result[feasible] = (bank.values(base[feasible]) + support).min(axis=1)
    return result


def timing_pair_count(low, high, budget):
    remaining = budget - int(low[0]) - int(low[1])
    a = min(int(high[0] - low[0]), remaining)
    b = min(int(high[1] - low[1]), remaining)
    if min(a, b, remaining) < 0:
        return 0
    excess = max(0, a + b - remaining)
    return (a + 1) * (b + 1) - excess * (excess + 1) // 2
