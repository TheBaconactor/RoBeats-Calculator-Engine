"""Brute-force parity for direct 2D grid gem_winners across stat caps, dominance, ties, sparse grids, and batch sizes."""
from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.frontier.fg_cache_patterns import surface_head_coeffs, surface_head_greats
from gear_optimizer.frontier.types import SurfacePool
from gear_optimizer.gamedata import stat_curves
from gear_optimizer.rules import ELEMENT_GEM_GAIN, MAX_STAT, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER, STAT_GEM_GAIN_NORMAL
from gear_optimizer.solver import gem_search as search
from gear_optimizer.stats import STAT_GEMS


def _pool_for_frontiers(frontier_count: int, seed: int, body_total: int = 8, head_len: int = 8) -> SurfacePool:
    rng = np.random.default_rng(seed)
    lengths = rng.integers(1, 4, frontier_count).astype(np.int32)
    offsets = np.concatenate(([0], np.cumsum(lengths)[:-1])).astype(np.int32)
    rows = int(lengths.sum())
    words = np.zeros((rows, 8), dtype=np.uint32)
    words[:, 0] = rng.integers(0, 1 << head_len, rows, dtype=np.uint32)
    counts = np.zeros((rows, 3), dtype=np.int32)
    counts[:, 0] = rng.integers(0, body_total + 1, rows, dtype=np.int32)
    return SurfacePool(
        frontier_offsets=offsets,
        frontier_lengths=lengths,
        pattern_ids=np.arange(rows, dtype=np.int32),
        pattern_words=words,
        counts=counts,
        head_coeffs=surface_head_coeffs(words, head_len=head_len),
        head_greats=surface_head_greats(words),
    )


def _brute_force_winner(loadout, budget, grid, pool, colors, curves, notes):
    flags = search.color_flags(*colors)
    ft_el, ff_el = STAT_GEMS["Fever Time"][1], STAT_GEMS["Fever Fill Rate"][1]
    ft_p, ft_s = int(colors[0] == ft_el) * STAT_GEM_ELEMENT_GAIN, int(colors[1] == ft_el) * STAT_GEM_ELEMENT_GAIN
    ff_p, ff_s = int(colors[0] == ff_el) * STAT_GEM_ELEMENT_GAIN, int(colors[1] == ff_el) * STAT_GEM_ELEMENT_GAIN
    gains = [STAT_GEM_ELEMENT_GAIN * int(flag) for flag in flags[:6]]
    ov_p, ov_s = ELEMENT_GEM_GAIN * int(flags[6]), ELEMENT_GEM_GAIN * int(flags[7])
    w_ov = (ov_p << 1) + ov_s
    allow_pp = gains[0] != 0 or gains[1] != 0
    ref_pp = np.ascontiguousarray(curves.f64["Perfect Points"])
    ref_cm = np.ascontiguousarray(curves.f64["Combo Multiplier"])
    ref_ramp = np.ascontiguousarray(curves.combo_ramp)
    ref_fm = np.ascontiguousarray(curves.f64["Fever Multiplier"])

    cur_pp, cur_cm, cur_fm, base_p, base_s, ft0, ff0 = (int(v) for v in loadout)
    ft_gain, ff_gain = (ft_p << 1) + ft_s, (ff_p << 1) + ff_s
    ft_caps = (ft_gain < w_ov) or (ft_gain == 0)
    ff_caps = (ff_gain < w_ov) or (ff_gain == 0)
    g = STAT_GEM_GAIN_FEVER
    ft_cap = min(budget, max(0, (MAX_STAT - ft0 + g - 1) // g)) if ft_caps else budget
    ff_cap = min(budget, max(0, (MAX_STAT - ff0 + g - 1) // g)) if ff_caps else budget

    by_fid: dict[int, list[tuple[int, int, int, int, int, int, int]]] = {}
    pos = 0
    for a in range(ft_cap + 1):
        ft_stat = min(MAX_STAT, max(0, ft0 + a * g))
        for b in range(min(ff_cap, budget - a) + 1):
            ff_stat = min(MAX_STAT, max(0, ff0 + b * g))
            fid = int(grid[ft_stat, ff_stat])
            r = budget - a - b
            pg, sg = a * ft_p + b * ff_p, a * ft_s + b * ff_s
            by_fid.setdefault(fid, []).append((a, b, r, (pg << 1) + sg + w_ov * r, pg, sg, pos + b))
        pos += budget + 1 - a

    ordered = []
    for fid, splits in by_fid.items():
        for s in splits:
            s_key = (s[2], s[3], s[4], s[5], s[6])
            if not any(o != s and search._dominates((o[2], o[3], o[4], o[5], o[6]), s_key) for o in splits):
                ordered.append((fid, s[0], s[1], s[2], s[4], s[5]))

    best = None
    for split_rank, (fid, a, b, residual, pg, sg) in enumerate(ordered):
        primary, secondary = base_p + pg, base_s + sg
        for ls in range(int(pool.frontier_lengths[fid])):
            sr = int(pool.frontier_offsets[fid]) + ls
            surface = tuple(int(v) for v in pool.counts[sr])
            for g_cm in range(min(residual, max(0, (MAX_STAT - cur_cm + STAT_GEM_GAIN_NORMAL - 1) // STAT_GEM_GAIN_NORMAL)) + 1):
                cm_mul = ref_cm[search._stat_row(cur_cm + g_cm * STAT_GEM_GAIN_NORMAL)]
                ramp = ref_ramp[search._stat_row(cur_cm + g_cm * STAT_GEM_GAIN_NORMAL)]
                for g_fm in range(min(residual - g_cm, max(0, (MAX_STAT - cur_fm + g - 1) // g)) + 1):
                    fm_mul = ref_fm[search._stat_row(cur_fm + g_fm * g)]
                    left = residual - g_cm - g_fm
                    pp_hi = min(left, max(0, (MAX_STAT - cur_pp + STAT_GEM_GAIN_NORMAL - 1) // STAT_GEM_GAIN_NORMAL)) if allow_pp else 0
                    for g_pp in range(pp_hi + 1):
                        g_ov = left - g_pp
                        score = search._surface_score(
                            pool.pattern_words[pool.pattern_ids[sr]], surface, notes,
                            primary + g_pp * gains[0] + g_cm * gains[2] + g_fm * gains[4] + g_ov * ov_p,
                            secondary + g_pp * gains[1] + g_cm * gains[3] + g_fm * gains[5] + g_ov * ov_s,
                            ref_pp[search._stat_row(cur_pp + g_pp * STAT_GEM_GAIN_NORMAL)],
                            (cm_mul, ramp, fm_mul), flags[8],
                        )
                        rank = (-score, split_rank, ls, g_cm, g_fm, g_pp)
                        if best is None or rank < best[0]:
                            best = (rank, a, b, (score, ls, g_pp, g_cm, g_fm, g_ov))
    return best[1], best[2], best[3]


def test_gem_winners_past_stat_caps_and_cap_vs_element():
    curves = stat_curves()
    grid = np.zeros((MAX_STAT + 1, MAX_STAT + 1), dtype=np.int32)
    pool = _pool_for_frontiers(1, seed=1)
    base = np.asarray(
        [[MAX_STAT, MAX_STAT, MAX_STAT, 40, 50, MAX_STAT, MAX_STAT], [1, 2, 3, 4, 5, 157, 158]],
        dtype=np.int32,
    )
    budgets = np.full(2, 8, dtype=np.int32)

    # Beat is FT's element and Vibe is FF's: with Beat selected (ov=+6 > ft=+3), past-cap FT/FF gems lose to element gems.
    winners_sel = search.gem_winners(base, (grid, pool), colors=("Beat", "Vibe", "Beat"), curves=curves, notes=(8, 8), budgets=budgets)
    assert winners_sel[0].ft == 0 and winners_sel[0].ff == 0
    # With no selected color (ov=0 < ft=+3), past-cap FT gems add primary Beat and win.
    winners_nosel = search.gem_winners(base, (grid, pool), colors=("Beat", "Vibe", ""), curves=curves, notes=(8, 8), budgets=budgets)
    assert winners_nosel[0].ft == 8

    for colors in (("Beat", "Vibe", "Beat"), ("Beat", "Vibe", ""), ("Vibe", "Rush", ""), ("Flow", "Rush", "Flow")):
        got = search.gem_winners(base, (grid, pool), colors=colors, curves=curves, notes=(8, 8), budgets=budgets)
        for row, w in zip(base, got, strict=True):
            exp_ft, exp_ff, exp_inner = _brute_force_winner(row, 8, grid, pool, colors, curves, (8, 8))
            assert (w.ft, w.ff, w.inner_row) == (exp_ft, exp_ff, exp_inner)


def test_gem_winners_exact_ties_within_and_across_frontiers():
    """Equal surfaces on distinct frontiers pick the first-reached frontier; equal splits on one frontier pick the
    dominating or earliest split."""
    curves = stat_curves()
    # Two distinct frontiers with identical surfaces, laid out non-monotonically on the grid.
    words = np.zeros((2, 8), dtype=np.uint32)
    counts = np.asarray([[4, 0, 0], [4, 0, 0]], dtype=np.int32)
    pool = SurfacePool(
        frontier_offsets=np.asarray([0, 1], dtype=np.int32),
        frontier_lengths=np.asarray([1, 1], dtype=np.int32),
        pattern_ids=np.asarray([0, 1], dtype=np.int32),
        pattern_words=words,
        counts=counts,
        head_coeffs=surface_head_coeffs(words, head_len=8),
        head_greats=surface_head_greats(words),
    )
    grid = np.zeros((MAX_STAT + 1, MAX_STAT + 1), dtype=np.int32)
    grid[0, 3:] = 1  # (ft=0, ff=0) hits frontier 0; (ft=0, ff>=1) hits frontier 1
    grid[3:, :] = 1
    base = np.asarray([[160, 160, 160, 100, 100, 0, 0], [160, 160, 160, 100, 100, 3, 0]], dtype=np.int32)
    budgets = np.asarray([6, 6], dtype=np.int32)
    for colors in (("Beat", "Flow", ""), ("Vibe", "Rush", ""), ("Vibe", "Rush", "Vibe")):
        got = search.gem_winners(base, (grid, pool), colors=colors, curves=curves, notes=(8, 8), budgets=budgets)
        for row, w in zip(base, got, strict=True):
            exp_ft, exp_ff, exp_inner = _brute_force_winner(row, 6, grid, pool, colors, curves, (8, 8))
            assert (w.ft, w.ff, w.inner_row) == (exp_ft, exp_ff, exp_inner)


@pytest.mark.parametrize("colors", [("Beat", "Flow", "Beat"), ("Vibe", "Rush", ""), ("Chill", "Chill", "Chill")])
@pytest.mark.parametrize("candidate_count", (1, 17, 64, 65))
def test_gem_winners_sparse_grid_and_batch_sizes_match_bruteforce(candidate_count, colors):
    curves = stat_curves()
    rng = np.random.default_rng(candidate_count * 31 + len(colors[0]))
    budget = 9
    base = np.concatenate(
        (rng.integers(0, 161, size=(candidate_count, 3)), rng.integers(0, 300, size=(candidate_count, 2)),
         rng.integers(0, 140, size=(candidate_count, 2))),
        axis=1,
    ).astype(np.int32)
    if colors[0] == colors[1]:
        base[:, 4] = base[:, 3]
    # Sparse grid: only reachable cells populated, with arbitrary non-contiguous frontier ids.
    frontier_count = 12
    pool = _pool_for_frontiers(frontier_count, seed=candidate_count + 7)
    grid = np.full((MAX_STAT + 1, MAX_STAT + 1), -1, dtype=np.int32)
    for ft0, ff0 in base[:, 5:7].tolist():
        for a in range(budget + 1):
            for b in range(budget - a + 1):
                x, y = min(MAX_STAT, ft0 + a * STAT_GEM_GAIN_FEVER), min(MAX_STAT, ff0 + b * STAT_GEM_GAIN_FEVER)
                grid[x, y] = (x // 12 + y // 12) % frontier_count
    budgets = np.full(candidate_count, budget, dtype=np.int32)
    memo = search.GemMemo()
    got = search.gem_winners(base, (grid, pool), colors=colors, curves=curves, notes=(8, 8), budgets=budgets, memo=memo)
    # Second call reuses memo identically.
    got2 = search.gem_winners(base, (grid, pool), colors=colors, curves=curves, notes=(8, 8), budgets=budgets, memo=memo)
    assert got == got2
    for row, w in zip(base[:12], got[:12], strict=True):
        exp_ft, exp_ff, exp_inner = _brute_force_winner(row, budget, grid, pool, colors, curves, (8, 8))
        assert (w.ft, w.ff, w.inner_row) == (exp_ft, exp_ff, exp_inner)


@pytest.mark.parametrize(
    "colors",
    [
        ("Beat", "Vibe", "Beat"),
        ("Vibe", "Beat", "Vibe"),
        ("Beat", "Chill", "Beat"),  # secondary Chill -> allow_pp True
        ("Chill", "Chill", "Chill"),  # single-color + allow_pp True
        ("Rush", "Flow", "Rush"),
    ],
)
def test_gem_winners_optimal_score_matches_unpruned_exhaustive_search(colors):
    """Independent exhaustive oracle: enumerates ALL legal 6-tuples (ft, ff, pp, cm, fm, ov) summing to budget
    with NO dominance pruning, NO stat-cap pruning, and independent scoring via gear_optimizer.score.fg_surface_score
    (primary selected, as every RoBeats solve uses)."""
    from gear_optimizer.frontier.types import FgResponseSurface
    from gear_optimizer.gamedata import empty_stats
    from gear_optimizer.score import factors as score_factors, fg_surface_score
    from gear_optimizer.stats import apply_gems, gems as make_gems

    curves = stat_curves()
    rng = np.random.default_rng(2026 + len(colors[0]) + len(colors[2]))
    head_len, body_total = 100, 12
    total_notes = head_len + body_total
    frontier_count = 6
    # Build surfaces with both Great-free and Great-bearing head/body patterns.
    lengths = np.full(frontier_count, 2, dtype=np.int32)
    offsets = np.arange(0, frontier_count * 2, 2, dtype=np.int32)
    rows = int(lengths.sum())
    words = np.zeros((rows, 8), dtype=np.uint32)
    words[:, 0] = rng.integers(0, 1 << 16, rows, dtype=np.uint32)
    words[1::2, 4] = rng.integers(0, 1 << 8, rows // 2, dtype=np.uint32)
    counts = np.zeros((rows, 3), dtype=np.int32)
    counts[:, 0] = rng.integers(0, body_total + 1, rows, dtype=np.int32)
    counts[1::2, 1] = rng.integers(0, 5, rows // 2, dtype=np.int32)
    counts[1::2, 2] = np.minimum(counts[1::2, 1], counts[1::2, 0])
    pool = SurfacePool(
        frontier_offsets=offsets,
        frontier_lengths=lengths,
        pattern_ids=np.arange(rows, dtype=np.int32),
        pattern_words=words,
        counts=counts,
        head_coeffs=surface_head_coeffs(words, head_len=head_len),
        head_greats=surface_head_greats(words),
    )
    grid = rng.integers(0, frontier_count, (MAX_STAT + 1, MAX_STAT + 1), dtype=np.int32)
    primary, secondary, selected = colors
    # Mix of uncapped, near-cap, and at-cap stats so every cap/dominance boundary is exercised.
    stat_rows = [
        {**empty_stats(), "Perfect Points": 157, "Combo Multiplier": 158, "Fever Multiplier": 156, "Fever Time": 155,
         "Fever Fill Rate": 158, primary: 120, secondary: 120 if primary == secondary else 75},
        {**empty_stats(), "Perfect Points": 160, "Combo Multiplier": 160, "Fever Multiplier": 160, "Fever Time": 160,
         "Fever Fill Rate": 160, primary: 80, secondary: 80 if primary == secondary else 40},
        {**empty_stats(), "Perfect Points": 10, "Combo Multiplier": 25, "Fever Multiplier": 40, "Fever Time": 12,
         "Fever Fill Rate": 18, primary: 200, secondary: 200 if primary == secondary else 90},
    ]
    budget = 6
    base = np.asarray(
        [[s["Perfect Points"], s["Combo Multiplier"], s["Fever Multiplier"], s[primary], s[secondary],
          s["Fever Time"], s["Fever Fill Rate"]] for s in stat_rows],
        dtype=np.int32,
    )
    winners = search.gem_winners(
        base, (grid, pool), colors=colors, curves=curves, notes=(head_len, body_total),
        budgets=np.full(len(stat_rows), budget, dtype=np.int32),
    )
    for base_dict, w in zip(stat_rows, winners, strict=True):
        best_score = -1
        for g_ft in range(budget + 1):
            for g_ff in range(budget - g_ft + 1):
                for g_cm in range(budget - g_ft - g_ff + 1):
                    for g_fm in range(budget - g_ft - g_ff - g_cm + 1):
                        for g_pp in range(budget - g_ft - g_ff - g_cm - g_fm + 1):
                            g_ov = budget - g_ft - g_ff - g_cm - g_fm - g_pp
                            final = apply_gems(
                                base_dict,
                                make_gems(pp=g_pp, cm=g_cm, fm=g_fm, ft=g_ft, ff=g_ff, element=g_ov),
                                selected,
                            )
                            fid = int(grid[min(MAX_STAT, final["Fever Time"]), min(MAX_STAT, final["Fever Fill Rate"])])
                            f = score_factors(final, curves, primary, secondary)
                            for ls in range(int(pool.frontier_lengths[fid])):
                                sr = int(pool.frontier_offsets[fid]) + ls
                                surf = FgResponseSurface(*pool.pattern_words[sr].tolist(), *pool.counts[sr].tolist())
                                sc = fg_surface_score(f, surf, total_notes)
                                if sc > best_score:
                                    best_score = sc
        score, _ls, g_pp, g_cm, g_fm, g_ov = w.inner_row
        assert score == best_score
        assert w.ft + w.ff + g_pp + g_cm + g_fm + g_ov == budget
        win_final = apply_gems(
            base_dict, make_gems(pp=g_pp, cm=g_cm, fm=g_fm, ft=w.ft, ff=w.ff, element=g_ov), selected
        )
        assert fg_surface_score(score_factors(win_final, curves, primary, secondary), FgResponseSurface(*w.surface), total_notes) == best_score
