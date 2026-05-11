from __future__ import annotations

import numpy as np


def test_exact_skyline_pair_code_pack_unpack_roundtrip() -> None:
    from gear_optimizer.solver.exact_skyline import _pack_pair_indices, _unpack_pair_codes

    gear_idx = np.asarray([0, 1, 12_345], dtype=np.int32)
    mini_idx = np.asarray([5, 7, 99], dtype=np.int32)

    codes = _pack_pair_indices(gear_idx, mini_idx)
    g2, m2 = _unpack_pair_codes(codes)

    assert np.array_equal(g2, gear_idx)
    assert np.array_equal(m2, mini_idx)


def test_mini_skyline_keeps_lower_ff_timing_cell_counterexample() -> None:
    from gear_optimizer.solver.mini_skyline import mini_combo_skyline
    from gear_optimizer.solver.solver_common import make_pack

    def mini(name: str, *, ff: int = 0) -> dict:
        return {
            "Name": name,
            "Rush": 50,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Time": 0,
            "Fever Fill Rate": int(ff),
        }

    mini_pool = [
        mini("low-a"),
        mini("low-b"),
        mini("low-c"),
        mini("high-a", ff=10),
        mini("high-b"),
        mini("high-c"),
    ]

    _stats, points, _codes = mini_combo_skyline(
        mini_pool,
        p_color="Rush",
        s_color="",
        pack=make_pack([len(mini_pool), len(mini_pool), len(mini_pool)]),
    )

    rows = {tuple(int(x) for x in row.tolist()) for row in points}
    assert (0, 0, 0, 0, 300) in rows
    assert (0, 0, 0, 10, 300) in rows


def test_combined_skyline_keeps_fixed_stat_different_ff_timing_cells() -> None:
    from gear_optimizer.solver.combined_skyline_sparse import combined_global_skyline_pairs_6d_sparse

    gear_points = np.asarray(
        [
            [0, 0, 0, 0, 0, 100],
            [0, 0, 0, 0, 10, 100],
        ],
        dtype=np.int32,
    )
    mini_points = np.asarray([[0, 0, 0, 0, 0]], dtype=np.int32)

    gear_idx, mini_idx = combined_global_skyline_pairs_6d_sparse(gear_points, mini_points)

    assert {(int(g), int(m)) for g, m in zip(gear_idx.tolist(), mini_idx.tolist(), strict=True)} == {
        (0, 0),
        (1, 0),
    }
