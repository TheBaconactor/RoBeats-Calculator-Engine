"""Exhaustive small-universe proofs for the outer bound (no production mocks)."""

from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import combinations, product
import math

import numpy as np
import pytest

from gear_optimizer.solver.scoring.exact_rescore import calculate_score_exact
from tools.research._core_bound_domain import catalog_domain, project
from tools.research._core_bound_math import (
    BoundBank, SCALE, certify_bounds, family_terms, fever_coefficients, log_interval,
    lookup_domain, prefix_census,
)


@pytest.mark.parametrize("value", [Fraction(1, 10000), Fraction(1, 3), 1, 2, 3, 10**9,
                                    Fraction.from_float(2.646777573)])
def test_log_enclosure_is_outward(value):
    lo, hi = log_interval(value)
    fraction = Fraction(value)
    with localcontext() as ctx:
        ctx.prec = 100
        exact = (Decimal(fraction.numerator) / Decimal(fraction.denominator)).ln()
        assert Decimal(lo) / SCALE <= exact <= Decimal(hi) / SCALE
    assert hi - lo <= 1


def test_lookup_preserves_negative_and_capped_raw_tails():
    x, y = lookup_domain((-4, 12), [200, 250, 225])
    assert x.tolist() == [-4, 0, 1, 2, 12]
    assert y.tolist() == [200, 200, 250, 225, 225]


def _allocations(budget):
    return np.array([g for g in product(range(budget + 1), repeat=6) if sum(g) <= budget], dtype=np.int64)


@pytest.mark.parametrize("notes,fever", [(7, 0), (7, 4), (103, 50), (103, 103)])
def test_head_bound_covers_all_fever_positions(notes, fever):
    normal, fever_weight = fever_coefficients(notes, fever, 2.0)
    for combo, multiplier in product([2.0, 2.67, 5.0], [1.0, 3.0, 5.425]):
        ramp = np.minimum(np.arange(1, notes + 1) / 100, 1)
        values = 1 + (combo - 1) * ramp
        optimistic = values.sum() + (multiplier - 1) * (values[-fever:].sum() if fever else 0)
        upper = combo * (float(normal) + float(fever_weight) * multiplier)
        assert optimistic <= upper + 1e-12


@pytest.mark.parametrize("seed", [7, 19])
def test_every_bound_covers_exhaustive_gear_minis_and_shared_gems(seed):
    rng = np.random.default_rng(seed)
    gear = [rng.integers(0, 5, (2, 6), dtype=np.int64) for _ in range(6)]
    # Negative gear PP and over-cap sums expose premature clipping errors.
    gear[0][0, 0] = -10
    mini = rng.integers(0, 5, (4, 6), dtype=np.int64)
    gem = np.eye(6, dtype=np.int64) * 2
    gem[:3, 5] = [3, 1, 2]
    fixed = np.array([0, 0, 0, 0, 0, 300], dtype=np.int64)
    allocations = _allocations(2)
    totals, families = [], []
    for choices in product(range(2), repeat=6):
        g = fixed + sum(gear[i][j] for i, j in enumerate(choices))
        for minis in combinations(range(4), 3):
            totals.extend(g + mini[list(minis)].sum(axis=0) + allocations @ gem)
            families.extend([choices] * len(allocations))
    totals = np.asarray(totals, dtype=np.int64)
    intervals = np.stack([totals.min(axis=0), totals.max(axis=0)], axis=1)
    # Non-concave and nonmonotone finite reference tables; tangent-only shortcuts fail.
    refs = {"Perfect Points": np.array([200., 230., 205., 270., 285.]),
            "Combo Multiplier": np.array([2., 2.1, 2.05, 2.4, 2.5]),
            "Fever Multiplier": np.array([3., 4., 3.5, 4.5, 5.])}
    coefficients = [[1 / b, 0.02, 0.013, 0.015, 0, 0] for b in (400, 600, 900)]
    bank = certify_bounds(coefficients, intervals=intervals, refs=refs, notes=7, fever_notes=4)
    mask = [False] * 3 + [True] * 4
    scores = np.array([calculate_score_exact(
        s[5] + refs["Perfect Points"][np.clip(s[0], 0, 4)],
        refs["Combo Multiplier"][np.clip(s[1], 0, 4)],
        refs["Fever Multiplier"][np.clip(s[2], 0, 4)], mask, 0, 0,
    ) for s in totals])
    score_logs = np.array([log_interval(int(score))[1] for score in scores])
    assert np.all(bank.values(totals) >= score_logs[:, None])
    root, losses = family_terms(bank, fixed=fixed, gear=gear, minis=mini, gems=gem, budget=2)
    # Every partial family bound still covers every legal completion, including gems.
    for depth in range(7):
        upper = np.tile(root, (len(totals), 1))
        for slot in range(depth):
            upper -= losses[slot][np.array(families)[:, slot]]
        assert np.all(upper >= score_logs[:, None])
        winners = scores == scores.max()
        assert np.all(upper[winners].min(axis=1) >= log_interval(int(scores.max()))[0])


def test_shared_budget_and_three_distinct_minis():
    bank = BoundBank(np.array([[1, 2, 3, 0, 0, 0]], dtype=np.int64), np.array([0]))
    gear = [np.zeros((1, 6), dtype=np.int64) for _ in range(6)]
    minis = np.array([[10, 0, 0, 0, 0, 0], [5, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0]])
    gems = np.eye(6, dtype=np.int64)
    root, _ = family_terms(bank, fixed=np.zeros(6, dtype=np.int64), gear=gear, minis=minis, gems=gems, budget=90)
    assert root[0] == 10 + 5 + 1 + 90 * 3
    assert root[0] < 3 * 10 + 90 * (1 + 2 + 3)


def test_item_losses_accumulate_and_threshold_ties_survive():
    threshold = log_interval(1000)[0]
    root = np.array([threshold + 5])
    losses = [np.array([[0], [3]]), np.array([[0], [3]])]
    census = prefix_census(root, losses, incumbent=1000, depth=2)
    assert census[0]["surviving"] == 2
    assert census[1]["surviving"] == 3
    tied = prefix_census(np.array([threshold]), [np.array([[0], [1]])], incumbent=1000, depth=1)
    assert tied[0]["surviving"] == 1


def test_catalog_keeps_all_minis_and_materializes_for_each_song():
    from gear_optimizer.data.csv_parser import load_csv_db
    from pathlib import Path
    data = Path(__file__).resolve().parents[1] / "Data/Gear"
    gears = list(load_csv_db(str(data / "Gears.csv"), "gear").values())
    minis = list(load_csv_db(str(data / "Minis.csv"), "mini").values())
    song = {"metadata": {"Song Name": "no target", "Primary Color": "Chill", "Secondary Color": "Chill"}}
    domain = catalog_domain(gears, minis, song=song, fixed={})
    assert len(domain.minis) == len(minis)
    assert sum(map(len, domain.gear)) == len(gears)
    assert domain.loadouts == math.prod(map(len, domain.gear)) * math.comb(len(minis), 3)
    # Same primary/secondary is a 3x lane in the authoritative score, not 2x.
    assert project({"Chill": 7}, "Chill", "Chill")[-1] == 21
    assert domain.gems[-1, 5] == 18
    target = next(m for m in minis if m.get("Song Target"))
    target_names = target["Song Target"]
    song["metadata"]["Song Name"] = target_names[0] if isinstance(target_names, list) else target_names
    targeted = catalog_domain(gears, minis, song=song, fixed={})
    assert not np.array_equal(targeted.minis, domain.minis)


def test_lazy_core_is_identical_to_exhaustive_family_filter():
    from types import SimpleNamespace
    from tools.research._core_bound_search import enumerate_core
    rng = np.random.default_rng(129)
    gear = [rng.integers(-3, 6, (2, 6), dtype=np.int64) for _ in range(6)]
    minis = rng.integers(-3, 6, (5, 6), dtype=np.int64)
    gems = np.eye(6, dtype=np.int64)
    fixed = np.zeros(6, dtype=np.int64)
    threshold = log_interval(1000)[0]
    bank = BoundBank(rng.integers(-4, 5, (3, 6), dtype=np.int64), np.full(3, threshold - 10))
    root, losses = family_terms(bank, fixed=fixed, gear=gear, minis=minis, gems=gems, budget=2)
    domain = SimpleNamespace(gear=gear, minis=minis, gems=gems, fixed=fixed, budget=2)
    region = SimpleNamespace(bank=bank, root=root, losses=losses)
    expected = set()
    support = 2 * np.maximum(0, (gems @ bank.weights.T).max(axis=0))
    for g in product(range(2), repeat=6):
        for m in combinations(range(5), 3):
            stats = fixed + sum(gear[i][j] for i, j in enumerate(g)) + minis[list(m)].sum(axis=0)
            if np.min(stats @ bank.weights.T + bank.intercepts + support) >= threshold:
                expected.add(g + m)
    assert expected
    assert len(expected) < 2**6 * math.comb(5, 3)
    result = enumerate_core(domain, [region, region], incumbent=1000)
    assert result.complete
    assert result.witnesses == expected  # Also dedupes witnesses across timing regions.
    limited = enumerate_core(domain, [region], incumbent=1000, max_nodes=1)
    assert not limited.complete
    assert limited.nodes == 1


def test_fg_relaxation_covers_forced_greats_on_every_small_head_mask():
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import (
        _fg_response_surface_score_native_f64,
    )
    refs = {"Perfect Points": np.array([200., 350., 485.]),
            "Combo Multiplier": np.array([2., 2.4, 2.67]),
            "Fever Multiplier": np.array([3., 4.75, 5.425])}
    intervals = np.array([[0, 2], [0, 2], [0, 2], [0, 0], [0, 0], [600, 600]])
    bank = certify_bounds([[1 / 1000, 0.01, 0.01, 0.01, 0, 0]], intervals=intervals,
                          refs=refs, notes=3, fever_notes=3)
    words = np.zeros((1, 8), dtype=np.uint32)
    for pp, cm, fm in product(range(3), repeat=3):
        stats = np.array([[pp, cm, fm, 0, 0, 600]], dtype=np.int64)
        upper = bank.values(stats)[0, 0]
        for fever, great in product(range(8), repeat=2):
            words[0, 0], words[0, 4] = fever, great
            score = _fg_response_surface_score_native_f64(words, 0, 0, 0, 0, 3, 0, 200, 200,
                refs["Perfect Points"][pp], refs["Combo Multiplier"][cm], refs["Fever Multiplier"][fm])
            assert log_interval(int(score))[1] <= upper


def test_float32_rounding_is_covered_near_a_tight_bound():
    from gear_optimizer.solver.score_math import fast_calculate_score
    for pp, cm, fm in [(473., 2.646777573, 5.366943932), (450.1, 2.6, 5.25), (485., 2.67, 5.425)]:
        refs = {"Perfect Points": [pp], "Combo Multiplier": [cm], "Fever Multiplier": [fm]}
        intervals = np.array([[0, 0]] * 5 + [[2580, 2580]])
        bank = certify_bounds([[1 / (2580 + pp), 0, 0, 0, 0, 0]], intervals=intervals,
                              refs=refs, notes=1709, fever_notes=1473)
        upper = bank.values(np.array([[0, 0, 0, 0, 0, 2580]], dtype=np.int64))[0, 0]
        for scorer in (calculate_score_exact, fast_calculate_score):
            score = scorer(2580 + pp, cm, fm, np.zeros(100, dtype=np.bool_), 1473, 136)
            assert log_interval(int(score))[1] <= upper


def test_regional_budget_keeps_unresolved_coverage():
    from types import SimpleNamespace
    from tools.research._core_bound_regions import refine_regions
    gear = [np.zeros((1, 6), dtype=np.int64) for _ in range(6)]
    gear[0] = np.array([[0, 0, 0, 0, 0, 0], [0, 0, 0, 2, 0, 0]])
    gear[1] = np.array([[0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 2, 0]])
    domain = SimpleNamespace(fixed=np.array([1, 1, 1, 0, 0, 300]), gear=gear,
        minis=np.zeros((3, 6), dtype=np.int64), gems=np.zeros((6, 6), dtype=np.int64), budget=0,
        intervals=np.array([[1, 1]] * 3 + [[0, 2], [0, 2], [300, 300]]))
    refs = {"Perfect Points": [200., 300.], "Combo Multiplier": [2., 2.5], "Fever Multiplier": [3., 4.]}
    fever = np.array([[1, 2, 0], [1, 7, 3], [2, 1, 6]])
    broad, regions, counts = refine_regions(domain, refs=refs, notes=7, fever_counts=fever,
        anchor_base=600, incumbent=1, max_leaves=3)
    assert broad.fever_notes == 7  # Independent FT/FF endpoints would miss the interior maximum.
    assert counts["regions_built"] <= 5
    assert not counts["certified"]
    for ft, ff in product([0, 2], repeat=2):
        covering = [r for r in regions if r.intervals[3, 0] <= ft <= r.intervals[3, 1]
                    and r.intervals[4, 0] <= ff <= r.intervals[4, 1]]
        assert len(covering) == 1
        assert covering[0].fever_notes >= fever[ft, ff]


def test_base_fever_summary_requires_complete_surface_coverage():
    from types import SimpleNamespace
    from tools.research._core_bound_domain import base_fever_counts
    payload = SimpleNamespace(grid_frontier_count=np.array([[[2, 1]]]),
        grid_frontier_offset=np.array([[[0, 2]]]), grid_frontier_body_fever_pool=np.array([[10, 12, 8]]),
        grid_frontier_head_coeffs_pool=np.array([[[0, 3, 0, 0], [0, 4, 0, 0], [0, 2, 0, 0]]]))
    assert base_fever_counts(payload).tolist() == [[16, 10]]
    payload.grid_frontier_count[0, 0, 1] = 0
    with pytest.raises(ValueError, match="every lookup cell"):
        base_fever_counts(payload)
