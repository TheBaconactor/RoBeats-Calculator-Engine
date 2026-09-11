"""Base warmstart parity with an unseeded, unpruned CM/FM enumeration."""

import numpy as np
import pytest
import taichi as ti

from gear_optimizer.helpers.song_helpers.ref_array_builder import get_exact_replay_ref_arrays_cached
from gear_optimizer.solver.taichi_gem.kernels import kernels_helpers as fields
from gear_optimizer.solver.taichi_gem.kernels.kernels_scoring import (
    calc_score_cached_device,
    score_solution_from_gems_frontier,
)
from gear_optimizer.solver.taichi_gem.kernels.warmstart_common import solve_combo_warmstart_preloaded

pytestmark = pytest.mark.gpu


@ti.kernel
def _set_frontiers():
    for combo in range(2):
        ft_idx = (combo + 1) * 3
        fields.ftff_combo_ft[combo] = combo + 1
        fields.ftff_combo_ff[combo] = 1
        fields.grid_head_len[0, ft_idx, 3] = 100
        fields.grid_count_body_fever[0, ft_idx, 3] = 40
        fields.grid_count_body_normal[0, ft_idx, 3] = 80
        fields.grid_frontier_count[0, ft_idx, 3] = 5
        fields.grid_frontier_offset[0, ft_idx, 3] = combo * 5
        for variant in range(5):
            pool = combo * 5 + variant
            fields.grid_frontier_body_fever_pool[0, pool] = 20 + variant * 5
            fields.grid_frontier_body_normal_pool[0, pool] = 100 - variant * 5
            masks = ti.Vector.zero(ti.u32, 4)
            coeffs = ti.Vector.zero(ti.i32, 4)
            for note in range(100):
                # Crossing surfaces retain different physical head witnesses.
                fever = ti.cast(((note + combo) % (2 + variant % 4)) == 0, ti.i32)
                if fever:
                    masks[note // 32] = masks[note // 32] | (ti.u32(1) << (note % 32))
                coeffs[fever] += 1
                coeffs[2 + fever] += note + 1
            for word in ti.static(range(4)):
                fields.grid_frontier_masks_bits_pool[0, pool, word] = masks[word]
                fields.grid_frontier_head_coeffs_pool[0, pool, word] = ti.cast(coeffs[word], ti.i16)


@ti.kernel
def _compare(
    stats: ti.types.ndarray(dtype=ti.i32, ndim=2),
    flags: ti.types.ndarray(dtype=ti.i32, ndim=2),
    actual: ti.types.ndarray(dtype=ti.i32, ndim=3),
    expected: ti.types.ndarray(dtype=ti.i32, ndim=3),
    rescored: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    for row, combo in ti.ndrange(stats.shape[0], 2):
        ft, ff = combo + 1, 1
        budget = stats[row, 5] - ft - ff
        pp, cm, fm = stats[row, 0], stats[row, 1], stats[row, 2]
        p = stats[row, 3] + 3 * (ft * flags[row, 0] + ff * flags[row, 2])
        s = stats[row, 4] + 3 * (ft * flags[row, 1] + ff * flags[row, 3])
        result = solve_combo_warmstart_preloaded(
            row,
            combo,
            stats[row, 5],
            3,
            flags[row, 0],
            flags[row, 1],
            flags[row, 2],
            flags[row, 3],
            flags[row, 4],
            flags[row, 5],
            flags[row, 6],
            flags[row, 7],
            flags[row, 8],
            flags[row, 9],
            flags[row, 10],
            flags[row, 11],
            0,
            0,
            0,
            pp,
            cm,
            fm,
            stats[row, 3],
            stats[row, 4],
            0,
            0,
            53,
            53,
            True,
            False,
            0,
        )
        for i in ti.static(range(5)):
            actual[row, combo, i] = result[i]
        rescored[row, combo] = score_solution_from_gems_frontier(
            ft,
            ff,
            result[1],
            result[2],
            result[3],
            result[4],
            pp,
            cm,
            fm,
            stats[row, 3],
            stats[row, 4],
            0,
            0,
            3,
            flags[row, 0],
            flags[row, 1],
            flags[row, 2],
            flags[row, 3],
            flags[row, 4],
            flags[row, 5],
            flags[row, 6],
            flags[row, 7],
            flags[row, 8],
            flags[row, 9],
            flags[row, 10],
            flags[row, 11],
            0,
            ft * 3,
            3,
            100,
        )
        max_pp = 0
        if flags[row, 4] or flags[row, 5]:
            max_pp = ti.min(budget, ti.max(0, (161 - pp) // 2))
        max_cm = ti.min(budget, ti.max(0, (161 - cm) // 2))
        max_fm = ti.min(budget, ti.max(0, (162 - fm) // 3))
        pp_key = flags[row, 4] | (flags[row, 5] << 1) | (flags[row, 10] << 2) | (flags[row, 11] << 3)
        best = ti.Vector([-1, 0, 0, 0, 0])
        for variant in range(5):
            surface = fields.read_timeline_frontier_variant(0, ft * 3, 3, variant)
            variant_best = ti.Vector([-1, 0, 0, 0, 0])
            for gc in range(max_cm + 1):
                for gf in range(ti.min(max_fm, budget - gc) + 1):
                    remaining = budget - gc - gf
                    gp = ti.cast(
                        fields.exact_pp_best_gems_prefix[pp_key, ti.min(160, pp), ti.min(max_pp, remaining)], ti.i32
                    )
                    go = remaining - gp
                    final_p = (
                        p + 3 * (gp * flags[row, 4] + gc * flags[row, 6] + gf * flags[row, 8]) + 6 * go * flags[row, 10]
                    )
                    final_s = (
                        s + 3 * (gp * flags[row, 5] + gc * flags[row, 7] + gf * flags[row, 9]) + 6 * go * flags[row, 11]
                    )
                    base = ti.cast(2 * final_p + final_s, ti.f32) + fields.lookup_ref_pp(pp + 2 * gp)
                    score = calc_score_cached_device(
                        base,
                        fields.lookup_ref_cm(cm + 2 * gc),
                        fields.lookup_ref_fm(fm + 3 * gf),
                        100,
                        surface.body_fever,
                        surface.body_normal,
                        surface.m0,
                        surface.m1,
                        surface.m2,
                        surface.m3,
                    )
                    if score > variant_best[0]:
                        variant_best = ti.Vector([score, gp, gc, gf, go])
            if variant_best[0] > best[0]:
                best = variant_best
        for i in ti.static(range(5)):
            expected[row, combo, i] = best[i]


def test_warmstart_reuses_exact_score_and_preserves_seed_ties():
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready

    ensure_ready(get_exact_replay_ref_arrays_cached())
    rng = np.random.default_rng(735)
    stats = np.array(
        [
            [40, 40, 40, 130, 70, 9],
            [159, 159, 159, 800, 500, 90],
            [160, 160, 160, 0, 0, 5],
            [161, 163, 161, 93, 39, 90],
            [0, 0, 0, 0, 0, 3],
        ]
        * 16,
        dtype=np.int32,
    )
    flags = rng.integers(0, 2, (len(stats), 12), dtype=np.int32)
    for i in range(len(stats)):
        key = i // 5
        flags[i, [4, 5, 10, 11]] = [(key >> bit) & 1 for bit in range(4)]
    actual = np.empty((len(stats), 2, 5), dtype=np.int32)
    expected = np.empty_like(actual)
    rescored = np.empty((len(stats), 2), dtype=np.int32)
    _set_frontiers()
    _compare(stats, flags, actual, expected, rescored)
    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(actual[:, :, 0], rescored)
    # GA's equal-score combo tie chooses the larger FT/FF combo index.
    np.testing.assert_array_equal(np.argmax(actual[:, ::-1, 0], axis=1), np.argmax(expected[:, ::-1, 0], axis=1))
