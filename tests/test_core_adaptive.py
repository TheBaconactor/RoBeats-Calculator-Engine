"""Coverage, constrained support, regional feedback, and actual GPU handoff."""

from itertools import product
from types import SimpleNamespace

import numpy as np
import pytest

from tools.research._core_bound_gems import constrained_support, gem_limits, regional_upper
from tools.research._core_bound_math import BoundBank, log_interval
from tools.research._core_bound_search import Candidate, CoreEnumeration
from tools.research._core_adaptive_score import region_queue


@pytest.mark.parametrize("seed", [13, 91, 204])
def test_greedy_affine_support_equals_exhaustive_box_budget(seed):
    rng = np.random.default_rng(seed)
    allocations = np.array([g for g in product(range(4), repeat=6) if sum(g) <= 3])
    gamma = rng.integers(-9, 10, (6, 7))
    for _ in range(25):
        low = np.zeros(6, dtype=np.int64)
        low[rng.integers(6)] = rng.integers(2)
        high = low + rng.integers(0, 3, 6)
        feasible = allocations[np.all((allocations >= low) & (allocations <= high), axis=1)]
        actual = constrained_support(gamma, low[None, :], high[None, :], 3)[0]
        assert np.array_equal(actual, (feasible @ gamma).max(axis=0))
        assert np.all(actual <= 3 * np.maximum(0, gamma.max(axis=0)))


@pytest.mark.parametrize("base_ft", [-8, 0, 157, 159, 160, 164])
def test_region_limits_keep_exact_raw_boundaries_and_cap_tails(base_ft):
    base = np.array([156, 159, 162, base_ft, -2, 500])
    for ft_low, ft_high in [(-20, 0), (1, 159), (160, 200), (-20, 200)]:
        region = np.array([[0, 999]] * 3 + [[ft_low, ft_high], [-10, 200], [0, 9999]])
        low, high, feasible = gem_limits(base, region, 3)
        for g in product(range(4), repeat=6):
            if sum(g) > 3:
                continue
            caps = np.maximum(0, (160 - base[[3, 4, 0, 1, 2]]) // [3, 3, 2, 2, 3])
            legal = np.all(np.array(g[:5]) <= caps)
            inside = ft_low <= base_ft + 3 * g[0] <= ft_high
            admitted = feasible and np.all(np.array(g) >= low) and np.all(np.array(g) <= high)
            assert bool(admitted) == bool(legal and inside)


def test_incomplete_enumeration_never_excludes_unvisited_regions():
    threshold = log_interval(1000)[0]
    region = SimpleNamespace(intervals=np.array([[0, 160]] * 5 + [[0, 9999]]),
                             bank=BoundBank(np.zeros((1, 6), dtype=np.int64), np.array([threshold])))
    core = CoreEnumeration((Candidate((0,) * 9, ((0, threshold),)),), (region, region),
                           1, False, (1,))
    domain = SimpleNamespace(gems=np.zeros((6, 6), dtype=np.int64), budget=0)
    rows, counts = region_queue(domain, core, np.zeros((1, 6), dtype=np.int64), 1000)
    assert [row[1] for row in rows] == [0]  # equality is kept
    assert counts["unvisited_regions"] == [1]  # unknown work remains pending
    rows, counts = region_queue(domain, core, np.zeros((1, 6), dtype=np.int64), 1001)
    assert rows == []  # the higher canonical incumbent authorizes these exclusions
    assert counts["unvisited_regions"] == [1]  # a higher incumbent cannot delete unknown work
    assert not core.complete  # unseen loadout identities still unresolved


def test_mandatory_timing_gems_tighten_only_survivor_bound():
    threshold = log_interval(1000)[0]
    # FT adds no value; PP is the only positive objective. A region requiring
    # two FT gems leaves at most one PP gem, not the unconstrained three.
    weights = np.array([[1, 0, 0, 0, 0, 0]], dtype=np.int64)
    region = SimpleNamespace(intervals=np.array([[0, 160]] * 3 + [[6, 9], [0, 160], [0, 9999]]),
                             bank=BoundBank(weights, np.array([threshold - 3])))
    gems = np.zeros((6, 6), dtype=np.int64)
    gems[0, 3], gems[2, 0] = 3, 2
    upper = regional_upper(np.zeros((1, 6), dtype=np.int64), region, gems, 3)[0]
    assert upper == threshold - 1
    assert threshold - 3 + 3 * 2 >= threshold


def test_matrix_is_reused_across_lambda_bank(monkeypatch):
    from tools.research import _core_bound_fit as fit
    calls = []
    original = fit.linprog

    def recorded(*args, **kwargs):
        calls.append((kwargs["A_ub"], kwargs["b_ub"].copy()))
        return original(*args, **kwargs)

    monkeypatch.setattr(fit, "linprog", recorded)
    domain = SimpleNamespace(fixed=np.array([0, 0, 0, 0, 0, 300]),
        gear=[np.zeros((1, 6), dtype=np.int64) for _ in range(6)],
        minis=np.zeros((3, 6), dtype=np.int64), gems=np.eye(6, dtype=np.int64), budget=3,
        intervals=np.array([[0, 3]] * 5 + [[300, 303]]))
    refs = {"Perfect Points": [200., 300.], "Combo Multiplier": [2., 2.5], "Fever Multiplier": [3., 4.]}
    fit.fit_bounds(domain, refs=refs, notes=7, fever_notes=4, anchor_base=500, members=3)
    assert len(calls) == 3
    assert all(matrix is calls[0][0] for matrix, _ in calls)
    assert not np.array_equal(calls[0][1], calls[1][1])


def test_timing_pair_count_equals_explicit_triangle_intersection():
    from tools.research._core_bound_gems import timing_pair_count
    for budget, lft, hft, lff, hff in product(range(4), repeat=5):
        low, high = np.array([lft, lff]), np.array([hft, hff])
        expected = sum(ft + ff <= budget for ft in range(lft, hft + 1) for ff in range(lff, hff + 1))
        assert timing_pair_count(low, high, budget) == expected
