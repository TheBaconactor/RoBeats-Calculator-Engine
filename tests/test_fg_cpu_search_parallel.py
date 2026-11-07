"""The CPU FG gem search split across cores equals one serial call, equals brute force on every allocation, keeps every
loadout that reaches its floor exact, and releases the GIL."""

import threading
import time

import numpy as np
import pytest

from gear_optimizer.gamedata import stat_curves
from gear_optimizer.rules import ELEMENT_GEM_GAIN, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER, STAT_GEM_GAIN_NORMAL
from gear_optimizer.solver import gem_search as search
from gear_optimizer.frontier.fg_cache_patterns import surface_head_coeffs, surface_head_greats


def _random_batch(key_count: int, seed: int, colors=("Chill", "Flow", "Chill"), head_len: int = 100, budget: int = 25):
    """Two loadouts per key; a key holds 1-5 groups, each on its own frontier of 1-8 surfaces."""
    rng = np.random.default_rng(seed)
    key_starts = np.concatenate(([0], np.cumsum(rng.integers(1, 6, key_count)))).astype(np.int64)
    group_count = int(key_starts[-1])
    groups = np.column_stack(
        [
            rng.integers(0, budget, group_count),  # residual gem budget
            rng.integers(0, 12, group_count),  # the split's primary gain
            rng.integers(0, 12, group_count),  # the split's secondary gain
            np.arange(group_count),  # its frontier
            np.zeros(group_count),  # its position among the splits
        ]
    ).astype(np.int32)
    loadouts = np.column_stack(
        [
            rng.integers(0, 161, (2 * key_count, 3)),  # PP, CM, FM
            rng.integers(0, 900, 2 * key_count),  # primary
            rng.integers(0, 500, 2 * key_count),  # secondary
            np.tile(np.arange(key_count), 2),  # its key
        ]
    ).astype(np.int32)
    if colors[0] == colors[1]:  # one color: its primary and secondary are one stat
        loadouts[:, 4] = loadouts[:, 3]
        groups[:, 2] = groups[:, 1]
    loadouts = np.ascontiguousarray(loadouts[np.lexsort(loadouts[:, 2::-1].T)])
    lengths = rng.integers(1, 9, group_count).astype(np.int64)
    offsets = np.concatenate(([0], np.cumsum(lengths)[:-1])).astype(np.int64)
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
    shapes = np.zeros((offsets.shape[0], 4), dtype=np.float64)
    search._frontier_shapes(
        groups[:, 3], offsets, lengths, pattern_ids, counts, head_coeffs, 120, shapes,
        np.zeros(offsets.shape[0], dtype=np.bool_),
    )
    surfaces = (offsets, lengths, shapes, pattern_ids, words, counts, head_coeffs, surface_head_greats(words))
    shared = (
        key_starts, groups, surfaces, np.array(search.color_flags(*colors), dtype=np.int32),
        tuple(
            np.ascontiguousarray(table, dtype=np.float64)
            for table in (curves.f64["Perfect Points"], curves.f64["Combo Multiplier"], curves.combo_ramp,
                          curves.f64["Fever Multiplier"])
        ),
        (head_len, 120, int((2 * groups[:, 1] + groups[:, 2]).max())),
    )
    return loadouts, shared


def _floors(loadouts):
    return np.full(loadouts.shape[0], -1, dtype=np.int64)


def _costs(loadouts, shared):
    key_starts, groups, surfaces = shared[:3]
    return np.add.reduceat(surfaces[1][groups[:, 3]], key_starts[:-1])[loadouts[:, 5]]


def _brute_force_row(loadout, shared):
    """The winner of a loadout by trying every group, surface and gem allocation."""
    key_starts, groups, surfaces, flags, (ref_pp, ref_cm, ref_ramp, ref_fm), (*notes, _most_gain) = shared
    offsets, lengths, _stats, pattern_ids, words, counts, _coeffs, _greats = surfaces
    cur_pp, cur_cm, cur_fm, base_primary, base_secondary, key = (int(v) for v in loadout)
    gains = [STAT_GEM_ELEMENT_GAIN * int(flag) for flag in flags[:6]]
    ov_p, ov_s = ELEMENT_GEM_GAIN * int(flags[6]), ELEMENT_GEM_GAIN * int(flags[7])
    allow_pp = gains[0] != 0 or gains[1] != 0
    pp_curve = search._gem_curve(ref_pp, cur_pp, STAT_GEM_GAIN_NORMAL, allow_pp)
    cm_curve = search._gem_curve(ref_cm, cur_cm, STAT_GEM_GAIN_NORMAL, True)
    fm_curve = search._gem_curve(ref_fm, cur_fm, STAT_GEM_GAIN_FEVER, True)
    best = None
    for g in range(key_starts[key], key_starts[key + 1]):
        residual, primary_gain, secondary_gain, frontier, _position = (int(v) for v in groups[g])
        primary, secondary = base_primary + primary_gain, base_secondary + secondary_gain
        for ls in range(int(lengths[frontier])):
            sr = int(offsets[frontier]) + ls
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
                        rank = (-score, g, ls, g_cm, g_fm, g_pp)
                        if best is None or rank < best[0]:
                            best = (rank, [score, ls, g_pp, g_cm, g_fm, g_ov])
    return best[0][1], best[1]


def test_parallel_search_equals_one_serial_call():
    for key_count, seed in ((1, 1), (7, 2), (33, 3), (257, 4), (1000, 5)):
        loadouts, shared = _random_batch(key_count, seed)
        serial = search._score_loadouts(loadouts, _floors(loadouts), *shared)
        parallel = search._score_on_cpu_cores(loadouts, _floors(loadouts), _costs(loadouts, shared), shared)
        np.testing.assert_array_equal(parallel[0], serial[0])
        np.testing.assert_array_equal(parallel[1], serial[1])


def test_winners_equal_trying_every_allocation():
    for key_count, seed, colors in ((12, 7, ("Chill", "Flow", "Chill")), (12, 8, ("Rush", "Rush", "Rush")),
                                    (12, 9, ("Flow", "Rush", "Rush")), (12, 10, ("Beat", "Chill", "Beat"))):
        loadouts, shared = _random_batch(key_count, seed, colors)
        rows, winners = search._score_loadouts(loadouts, _floors(loadouts), *shared)
        for loadout, row, winner in zip(loadouts, rows, winners):
            expected_group, expected_row = _brute_force_row(loadout, shared)
            assert int(winner) == expected_group
            assert row.tolist() == [int(value) for value in expected_row]


def test_a_floor_at_the_best_score_still_finds_the_winner():
    """No slack: a bound that falls below the winner's score loses it here."""
    for seed, colors in ((11, ("Chill", "Flow", "Chill")), (12, ("Rush", "Rush", "Rush")), (13, ("Flow", "Rush", "Rush")),
                         (14, ("Beat", "Chill", "Beat")), (15, ("Vibe", "Rush", "Vibe"))):
        loadouts, shared = _random_batch(3, seed, colors, budget=61)
        expected = [_brute_force_row(loadout, shared) for loadout in loadouts]
        rows, winners = search._score_loadouts(
            loadouts, np.asarray([row[0] for _group, row in expected], dtype=np.int64), *shared
        )
        assert winners.tolist() == [group for group, _row in expected]
        assert rows.tolist() == [[int(value) for value in row] for _group, row in expected]


@pytest.mark.parametrize("gem_bases, stats", [
    ((0, 0, 6), (40, 30, 30)), ((0, 2, 6), (0, 0, 0)), ((3, 0, 3), (150, 90, 20)), ((0, 0, 6), (160, 150, 0)), ((6, 3, 3), (80, 0, 160)),
])
def test_a_budget_bounds_its_columns_and_a_column_its_blocks_over_the_deltas(gem_bases, stats):
    curves = stat_curves()
    pp = search._gem_curve(np.ascontiguousarray(curves.f64["Perfect Points"]), stats[0], STAT_GEM_GAIN_NORMAL, False)
    cm = search._gem_curve(np.ascontiguousarray(curves.f64["Combo Multiplier"]), stats[1], STAT_GEM_GAIN_NORMAL, True)
    fm = search._gem_curve(np.ascontiguousarray(curves.f64["Fever Multiplier"]), stats[2], STAT_GEM_GAIN_FEVER, True)
    tables = search._block_bound_tables()
    term_max, column_combo, column_first, column_terms, blocks, corners = tables
    delta_lo, delta_hi = 150.0, 3000.0
    search._fill_block_bounds(tables, gem_bases, pp, cm, fm, (delta_lo, delta_hi))
    rng = np.random.default_rng(16)
    for _ in range(300):
        shape = tuple(rng.uniform(0.0, 900.0, 4).tolist())
        budget = int(rng.integers(0, search.GEM_BUDGET + 1))
        delta = rng.uniform(delta_lo, delta_hi - budget * gem_bases[2] - pp[0])
        budget_delta = delta + budget * gem_bases[2] + pp[0]
        best_column = 0.0
        for j in range(min(len(cm) - 1, budget) // search._TILE + 1):
            last = min(len(fm) - 1, budget - j * search._TILE) // search._TILE
            top = column_terms[j, last]
            column = search._column_bound(column_combo[j], top, budget_delta, shape)
            best_block = max(
                search._block_bound(blocks[bi], budget_delta, shape)
                for bi in range(column_first[j], column_first[j] + last + 1)
            )
            assert column >= best_block - 1e-6
            best_column = max(best_column, column)
        assert search._budget_bound(term_max[budget], delta, shape) >= best_column - 1e-6


def test_a_surface_ceiling_holds_every_live_block():
    rng = np.random.default_rng(17)
    for _ in range(3000):
        live = int(rng.integers(1, 8))
        blocks = np.zeros((live, 5), dtype=np.float64)
        blocks[:, 0] = rng.uniform(-300.0, 300.0, live)
        blocks[:, 3], blocks[:, 4] = rng.uniform(2.0, 2.6, live), rng.uniform(3.0, 5.2, live)
        blocks[:, 1], blocks[:, 2] = blocks[:, 3] + rng.uniform(0.0, 0.07, live), blocks[:, 4] + rng.uniform(0.0, 0.2, live)
        deltas = rng.uniform(400.0, 3000.0, live)
        frontier = tuple(rng.uniform(0.0, 900.0, 4).tolist())
        shape = tuple((np.asarray(frontier) * rng.uniform(0.0, 1.0, 4)).tolist())
        great = (*rng.uniform(0.0, 9000.0, 3).tolist(), float(rng.uniform(-90.0, 9000.0)))
        summary = search._live_summary(blocks, np.arange(live), deltas, live, frontier)
        ceiling = search._surface_ceiling(summary, frontier, shape, great)
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
    summary = search._live_summary(blocks, np.arange(2), deltas, 2, shape)
    expected = search._block_bound(blocks[0], 900.0, shape) - search._shape_value(great, 2.1, 3.1)
    assert search._surface_ceiling(summary, shape, shape, great) == pytest.approx(expected)


def test_a_stat_line_range_holds_the_deltas_of_its_loadouts():
    prefix = np.asarray([210.0, 240.0, 251.0], dtype=np.float64)
    loadouts = np.asarray([
        [40, 30, 30, 500, 300, 0], [40, 30, 30, 900, 100, 1], [40, 30, 30, 20, 950, 2], [41, 30, 30, 9000, 9000, 3],
    ], dtype=np.int32)
    colors = 2 * loadouts[:3, 3] + loadouts[:3, 4]
    low, high = search._stat_line_deltas(loadouts, 0, 70, 540, prefix)
    assert low <= colors.min() + prefix[0]
    assert high >= colors.max() + 70 + 540 + prefix[-1]
    assert search._stat_line_deltas(loadouts, 3, 0, 0, prefix)[0] == 27000 + prefix[0]


def test_search_kernel_releases_the_gil():
    loadouts, shared = _random_batch(20000, 9)
    search._score_loadouts(loadouts[:2], _floors(loadouts[:2]), *shared)  # compile outside the measurement
    done = threading.Event()
    kernel = {}

    def run_kernel():
        kernel["start"] = time.perf_counter()
        search._score_loadouts(loadouts, _floors(loadouts), *shared)
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
    loadouts, shared = _random_batch(1000, 6)
    rows, winners = search._score_loadouts(loadouts, _floors(loadouts), *shared)
    floors = rows[:, 0] + np.arange(loadouts.shape[0]) % 2  # every other loadout one point out of reach
    got, got_winners = search._score_loadouts(loadouts, floors, *shared)
    for k in range(loadouts.shape[0]):
        if k % 2 == 0:
            np.testing.assert_array_equal(got[k], rows[k])
            assert got_winners[k] == winners[k]
        else:
            assert got[k, 0] < floors[k]
