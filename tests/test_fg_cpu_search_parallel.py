"""The CPU FG gem search split across cores equals one serial call, equals brute force on every allocation and tie-break,
keeps every loadout that reaches its floor exact, and releases the GIL."""

import threading
import time

import numpy as np
import pytest

from gear_optimizer.frontier.fg_cache_patterns import surface_head_coeffs, surface_head_greats
from gear_optimizer.gamedata import stat_curves
from gear_optimizer.rules import ELEMENT_GEM_GAIN, MAX_STAT, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER, STAT_GEM_GAIN_NORMAL
from gear_optimizer.solver import gem_search as search
from gear_optimizer.stats import STAT_GEMS


def _random_batch(
    loadout_count: int,
    seed: int,
    colors=("Chill", "Flow", "Chill"),
    head_len: int = 100,
    budget: int = 25,
    frontier_count: int = 24,
):
    """Random loadouts (7 cols: PP, CM, FM, primary, secondary, FT, FF) on a random 161 x 161 frontier grid."""
    rng = np.random.default_rng(seed)
    # Assign frontiers by coarse (FT // 30, FF // 30) plus noise so frontiers repeat and also vary across splits.
    grid = rng.integers(0, frontier_count, (MAX_STAT + 1, MAX_STAT + 1), dtype=np.int32)
    loadouts = np.column_stack(
        [
            rng.integers(0, 161, (loadout_count, 3)),  # PP, CM, FM
            rng.integers(0, 900, loadout_count),  # primary
            rng.integers(0, 500, loadout_count),  # secondary
            rng.integers(0, 161, (loadout_count, 2)),  # FT, FF
        ]
    ).astype(np.int32)
    if colors[0] == colors[1]:  # one color: its primary and secondary are one stat
        loadouts[:, 4] = loadouts[:, 3]
    budgets = rng.integers(0, budget + 1, loadout_count, dtype=np.int32)
    flags = search.color_flags(*colors)
    allow_pp = bool(flags[0] or flags[1])
    order = np.lexsort(loadouts[:, 2::-1].T) if allow_pp else np.lexsort(loadouts[:, 2:0:-1].T)
    loadouts = np.ascontiguousarray(loadouts[order])
    budgets = np.ascontiguousarray(budgets[order])

    lengths = rng.integers(1, 9, frontier_count).astype(np.int32)
    offsets = np.concatenate(([0], np.cumsum(lengths)[:-1])).astype(np.int32)
    surface_rows = int(lengths.sum())
    patterns = 16
    words = rng.integers(0, 2**32, (patterns, 8), dtype=np.uint32)
    words[:, [3, 7]] &= np.uint32(0xF)  # a head has 100 notes
    words[:4, 4:] = 0  # some surfaces without Greats
    body_great = rng.integers(0, 60, surface_rows)
    counts = np.column_stack([rng.integers(0, 121, surface_rows), body_great, rng.integers(0, 40, surface_rows)])
    counts[:, 2] = np.minimum(counts[:, 2], counts[:, 1])
    counts = counts.astype(np.int32)
    pattern_ids = rng.integers(0, patterns, surface_rows).astype(np.int32)
    head_coeffs = surface_head_coeffs(words, head_len=head_len)
    curves = stat_curves()
    shapes = np.zeros((frontier_count, 4), dtype=np.float64)
    search._frontier_shapes(
        grid.ravel(), (offsets, lengths, pattern_ids, counts, head_coeffs), 120, shapes,
        np.zeros(frontier_count, dtype=np.bool_),
    )
    grid_info = (grid, *search._build_grid_bounds(grid, shapes))
    surfaces = (offsets, lengths, shapes, pattern_ids, words, counts, head_coeffs, surface_head_greats(words))
    ft_el, ff_el = STAT_GEMS["Fever Time"][1], STAT_GEMS["Fever Fill Rate"][1]
    song_cfg = (
        head_len, 120,
        int(colors[0] == ft_el) * STAT_GEM_ELEMENT_GAIN, int(colors[1] == ft_el) * STAT_GEM_ELEMENT_GAIN,
        int(colors[0] == ff_el) * STAT_GEM_ELEMENT_GAIN, int(colors[1] == ff_el) * STAT_GEM_ELEMENT_GAIN,
    )
    shared = (
        grid_info, surfaces, np.array(flags, dtype=np.int32),
        tuple(
            np.ascontiguousarray(table, dtype=np.float64)
            for table in (curves.f64["Perfect Points"], curves.f64["Combo Multiplier"], curves.combo_ramp,
                          curves.f64["Fever Multiplier"])
        ),
        song_cfg,
    )
    return loadouts, budgets, shared


def _floors(loadouts):
    return np.full(loadouts.shape[0], -1, dtype=np.int64)


def _curve(ref, stat, gain, allowed):
    out = np.empty(search.GEM_BUDGET + 1, dtype=np.float64)
    n = search._fill_gem_curve(out, ref, stat, gain, allowed)
    return out[: n + 1]


def _brute_force_row(loadout, budget, shared):
    """The winner of a loadout by trying every reachable (FT, FF) split, surface, and inner gem allocation, with the
    exact first-reached frontier and undominated split tie-break order."""
    grid_info, surfaces, flags, (ref_pp, ref_cm, ref_ramp, ref_fm), song_cfg = shared
    grid = grid_info[0]
    offsets, lengths, _shapes, pattern_ids, words, counts, _coeffs, _greats = surfaces
    head_len, body_total, ft_p, ft_s, ff_p, ff_s = song_cfg
    notes = (head_len, body_total)
    cur_pp, cur_cm, cur_fm, base_primary, base_secondary, ft0, ff0 = (int(v) for v in loadout)
    budget = int(budget)
    gains = [STAT_GEM_ELEMENT_GAIN * int(flag) for flag in flags[:6]]
    ov_p, ov_s = ELEMENT_GEM_GAIN * int(flags[6]), ELEMENT_GEM_GAIN * int(flags[7])
    w_ov = (ov_p << 1) + ov_s
    allow_pp = gains[0] != 0 or gains[1] != 0
    pp_curve = _curve(ref_pp, cur_pp, STAT_GEM_GAIN_NORMAL, allow_pp)
    cm_curve = _curve(ref_cm, cur_cm, STAT_GEM_GAIN_NORMAL, True)
    fm_curve = _curve(ref_fm, cur_fm, STAT_GEM_GAIN_FEVER, True)

    # First-reached frontier order and per-frontier undominated splits (matching the exact dominance spec).
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
            val = (pg << 1) + sg + w_ov * r
            by_fid.setdefault(fid, []).append((a, b, r, val, pg, sg, pos + b))
        pos += budget + 1 - a

    ordered_splits = []
    for fid, splits in by_fid.items():
        for s in splits:
            s_key = (s[2], s[3], s[4], s[5], s[6])
            if not any(
                o != s and search._dominates((o[2], o[3], o[4], o[5], o[6]), s_key)
                for o in splits
            ):
                ordered_splits.append((fid, s[0], s[1], s[2], s[4], s[5]))

    best = None
    for split_rank, (fid, a, b, residual, pg, sg) in enumerate(ordered_splits):
        primary, secondary = base_primary + pg, base_secondary + sg
        for ls in range(int(lengths[fid])):
            sr = int(offsets[fid]) + ls
            surface = tuple(int(v) for v in counts[sr])
            for g_cm in range(min(len(cm_curve) - 1, residual) + 1):
                ramp = ref_ramp[search._stat_row(cur_cm + g_cm * STAT_GEM_GAIN_NORMAL)]
                for g_fm in range(min(len(fm_curve) - 1, residual - g_cm) + 1):
                    left = residual - g_cm - g_fm
                    for g_pp in range(min(len(pp_curve) - 1, left) + 1):
                        g_ov = left - g_pp
                        final_primary = primary + g_pp * gains[0] + g_cm * gains[2] + g_fm * gains[4] + g_ov * ov_p
                        final_secondary = secondary + g_pp * gains[1] + g_cm * gains[3] + g_fm * gains[5] + g_ov * ov_s
                        score = search._surface_score(
                            words[pattern_ids[sr]], surface, notes, final_primary, final_secondary, pp_curve[g_pp],
                            (cm_curve[g_cm], ramp, fm_curve[g_fm]), flags[8],
                        )
                        rank = (-score, split_rank, ls, g_cm, g_fm, g_pp)
                        if best is None or rank < best[0]:
                            best = (rank, [a, b, fid], [score, ls, g_pp, g_cm, g_fm, g_ov])
    return best[1], best[2]


def test_parallel_search_equals_one_serial_call():
    for count, seed in ((1, 1), (7, 2), (33, 3), (257, 4), (600, 5)):
        loadouts, budgets, shared = _random_batch(count, seed)
        serial = search._score_grid_loadouts(loadouts, budgets, _floors(loadouts), *shared)
        parallel = search._score_on_cpu_cores(loadouts, budgets, _floors(loadouts), shared)
        np.testing.assert_array_equal(parallel[0], serial[0])
        np.testing.assert_array_equal(parallel[1], serial[1])


def test_winners_equal_trying_every_allocation():
    for count, seed, colors in (
        (10, 7, ("Chill", "Flow", "Chill")),
        (10, 8, ("Rush", "Rush", "Rush")),
        (10, 9, ("Flow", "Rush", "Rush")),
        (10, 10, ("Beat", "Chill", "Beat")),
        (10, 11, ("Vibe", "Rush", "Beat")),  # selected off-color -> ft_caps / ff_caps False
    ):
        loadouts, budgets, shared = _random_batch(count, seed, colors, budget=14)
        rows, winners = search._score_grid_loadouts(loadouts, budgets, _floors(loadouts), *shared)
        for loadout, budget, row, winner in zip(loadouts, budgets, rows, winners):
            expected_ftff, expected_row = _brute_force_row(loadout, budget, shared)
            assert winner.tolist() == expected_ftff
            assert row.tolist() == [int(value) for value in expected_row]


def test_a_floor_at_the_best_score_still_finds_the_winner():
    """No slack: a bound that falls below the winner's score loses it here."""
    for seed, colors in (
        (11, ("Chill", "Flow", "Chill")),
        (12, ("Rush", "Rush", "Rush")),
        (13, ("Flow", "Rush", "Rush")),
        (14, ("Beat", "Chill", "Beat")),
        (15, ("Vibe", "Rush", "Vibe")),
    ):
        loadouts, budgets, shared = _random_batch(6, seed, colors, budget=18)
        expected = [_brute_force_row(loadout, budget, shared) for loadout, budget in zip(loadouts, budgets)]
        rows, winners = search._score_grid_loadouts(
            loadouts, budgets, np.asarray([row[0] for _ftff, row in expected], dtype=np.int64), *shared
        )
        assert winners.tolist() == [ftff for ftff, _row in expected]
        assert rows.tolist() == [[int(value) for value in row] for _ftff, row in expected]


@pytest.mark.parametrize("gem_bases, stats", [
    ((0, 0, 6), (40, 30, 30)), ((0, 2, 6), (0, 0, 0)), ((3, 0, 3), (150, 90, 20)), ((0, 0, 6), (160, 150, 0)), ((6, 3, 3), (80, 0, 160)),
])
def test_a_budget_bounds_its_columns_and_a_column_its_blocks_over_the_deltas(gem_bases, stats):
    curves = stat_curves()
    pp = _curve(np.ascontiguousarray(curves.f64["Perfect Points"]), stats[0], STAT_GEM_GAIN_NORMAL, False)
    cm = _curve(np.ascontiguousarray(curves.f64["Combo Multiplier"]), stats[1], STAT_GEM_GAIN_NORMAL, True)
    fm = _curve(np.ascontiguousarray(curves.f64["Fever Multiplier"]), stats[2], STAT_GEM_GAIN_FEVER, True)
    tables = search._block_bound_tables()
    term_max, column_combo, column_first, column_terms, blocks, corners = tables
    delta_lo, delta_hi = 150.0, 3000.0
    limits = (0, len(cm) - 1, len(fm) - 1, False)
    search._fill_column_terms(column_combo, column_terms, gem_bases, cm, fm, limits, (delta_lo, delta_hi))
    search._fill_blocks(column_first, blocks, corners, gem_bases, cm, fm, limits)
    term_done = np.zeros(search.GEM_BUDGET + 1, dtype=np.bool_)
    term_ctx = (term_max, term_done, column_combo, column_terms, pp, 0.0, gem_bases[2], limits)
    rng = np.random.default_rng(16)
    for _ in range(300):
        shape = tuple(rng.uniform(0.0, 900.0, 4).tolist())
        budget = int(rng.integers(0, search.GEM_BUDGET + 1))
        delta = rng.uniform(delta_lo, delta_hi - budget * gem_bases[2])
        budget_delta = delta + budget * gem_bases[2]
        best_column = 0.0
        for j in range(min(len(cm) - 1, budget) // search._TILE_CM + 1):
            last = min(len(fm) - 1, budget - j * search._TILE_CM) // search._TILE_FM
            top = column_terms[j, last]
            column = search._column_bound(column_combo[j], top, budget_delta - delta_lo, shape)
            best_block = max(
                search._block_bound(blocks[bi], budget_delta, shape)
                for bi in range(column_first[j], column_first[j] + last + 1)
            )
            assert column >= best_block - 1e-6
            best_column = max(best_column, column)
        assert search._budget_bound(search._ensure_term_max(budget, term_ctx), delta - delta_lo, shape) >= best_column - 1e-6


def test_a_surface_ceiling_holds_every_live_block():
    rng = np.random.default_rng(17)
    for _ in range(3000):
        live = int(rng.integers(1, 8))
        blocks = np.zeros((live, 5), dtype=np.float64)
        blocks[:, 0] = rng.uniform(-300.0, 300.0, live)
        blocks[:, 3], blocks[:, 4] = rng.uniform(2.0, 2.6, live), rng.uniform(3.0, 5.2, live)
        blocks[:, 1], blocks[:, 2] = blocks[:, 3] + rng.uniform(0.0, 0.07, live), blocks[:, 4] + rng.uniform(0.0, 0.2, live)
        deltas = rng.uniform(400.0, 3000.0, live)
        body_sum, head_sum = float(rng.uniform(100.0, 1000.0)), float(rng.uniform(10.0, 100.0))
        fa, ff = float(rng.uniform(0.0, body_sum)), float(rng.uniform(0.0, head_sum))
        sa, sf = float(rng.uniform(0.0, fa)), float(rng.uniform(0.0, ff))
        frontier = (fa, body_sum - fa, ff, head_sum - ff)
        shape = (sa, body_sum - sa, sf, head_sum - sf)
        great = (*rng.uniform(0.0, 9000.0, 3).tolist(), float(rng.uniform(-90.0, 9000.0)))
        peak, low_base, low_combo, low_fever, low_wc, low_wf = search._live_summary(
            blocks, np.arange(live), deltas, live, frontier
        )
        ceil_df = low_base * (low_fever - 1.0)
        ceil_params = (peak, ceil_df * low_combo, ceil_df, low_wc, low_wf, low_wc * low_wf)
        ceiling = search._surface_ceiling(ceil_params, frontier, shape, great)
        worst = max(
            search._block_bound(block, delta, shape) - search._shape_value(great, block[3], block[4])
            for block, delta in zip(blocks, deltas)
        )
        assert ceiling >= worst - 1e-6


def test_a_surface_ceiling_takes_the_least_any_live_block_loses():
    blocks = np.asarray([[100.0, 2.5, 5.0, 2.1, 3.1], [100.0, 2.5, 5.0, 2.4, 4.9]], dtype=np.float64)
    deltas = np.asarray([900.0, 900.0], dtype=np.float64)
    shape = (500.0, 400.0, 30.0, 20.0)
    great = (1000.0, 1000.0, 1000.0, 0.0)
    peak, low_base, low_combo, low_fever, low_wc, low_wf = search._live_summary(
        blocks, np.arange(2), deltas, 2, shape
    )
    ceil_df = low_base * (low_fever - 1.0)
    ceil_params = (peak, ceil_df * low_combo, ceil_df, low_wc, low_wf, low_wc * low_wf)
    expected = search._block_bound(blocks[0], 900.0, shape) - search._shape_value(great, 2.1, 3.1)
    assert search._surface_ceiling(ceil_params, shape, shape, great) == pytest.approx(expected)


def test_a_stat_line_range_holds_the_deltas_of_its_loadouts():
    ref_pp = np.ascontiguousarray(stat_curves().f64["Perfect Points"])
    prefix = np.asarray([210.0, 240.0, 251.0], dtype=np.float64)
    loadouts = np.asarray([
        [40, 30, 30, 500, 300, 0, 0], [40, 30, 30, 900, 100, 1, 0], [40, 30, 30, 20, 950, 2, 0], [41, 30, 30, 9000, 9000, 3, 0],
    ], dtype=np.int32)
    colors = 2 * loadouts[:3, 3] + loadouts[:3, 4]
    low, high = search._stat_line_deltas(loadouts, 0, True, ref_pp, 70, 540, prefix, 2)
    assert low <= colors.min() + prefix[0]
    assert high >= colors.max() + 70 + 540 + prefix[-1]
    assert search._stat_line_deltas(loadouts, 3, True, ref_pp, 0, 0, prefix, 2)[0] == 27000 + prefix[0]
    all_vals = 2 * loadouts[:, 3] + loadouts[:, 4] + ref_pp[loadouts[:, 0]]
    low_nc, high_nc = search._stat_line_deltas(loadouts, 0, False, ref_pp, 70, 540, prefix, 0)
    assert low_nc <= all_vals.min()
    assert high_nc >= all_vals.max() + 70 + 540


def test_search_kernel_releases_the_gil():
    loadouts, budgets, shared = _random_batch(2000, 9, budget=45)
    search._score_grid_loadouts(loadouts[:2], budgets[:2], _floors(loadouts[:2]), *shared)  # compile outside the measurement
    done = threading.Event()
    kernel = {}

    def run_kernel():
        kernel["start"] = time.perf_counter()
        search._score_grid_loadouts(loadouts, budgets, _floors(loadouts), *shared)
        kernel["stop"] = time.perf_counter()
        done.set()

    worker = threading.Thread(target=run_kernel)
    longest_gap = 0.0
    last = time.perf_counter()
    worker.start()
    while not done.is_set():
        now = time.perf_counter()
        if "start" in kernel:
            longest_gap = max(longest_gap, now - last)
        last = now
    worker.join()
    kernel_seconds = kernel["stop"] - kernel["start"]
    # A GIL-holding kernel starves this thread for its whole run; a nogil one only for a switch.
    assert kernel_seconds > 0.05
    assert longest_gap < kernel_seconds / 2


def test_floors_keep_every_loadout_that_reaches_them_exact():
    loadouts, budgets, shared = _random_batch(400, 6)
    rows, winners = search._score_grid_loadouts(loadouts, budgets, _floors(loadouts), *shared)
    floors = rows[:, 0] + np.arange(loadouts.shape[0]) % 2  # every other loadout one point out of reach
    got, got_winners = search._score_grid_loadouts(loadouts, budgets, floors, *shared)
    for k in range(loadouts.shape[0]):
        if k % 2 == 0:
            np.testing.assert_array_equal(got[k], rows[k])
            np.testing.assert_array_equal(got_winners[k], winners[k])
        else:
            assert got[k, 0] < floors[k]
