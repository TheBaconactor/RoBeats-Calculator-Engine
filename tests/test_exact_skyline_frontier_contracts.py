from __future__ import annotations

import numpy as np
import pytest


def test_exact_skyline_pair_code_pack_unpack_roundtrip() -> None:
    from tests.parity.exact_skyline import _pack_pair_indices, _unpack_pair_codes

    gear_idx = np.asarray([0, 1, 12_345], dtype=np.int32)
    mini_idx = np.asarray([5, 7, 99], dtype=np.int32)

    codes = _pack_pair_indices(gear_idx, mini_idx)
    g2, m2 = _unpack_pair_codes(codes)

    assert np.array_equal(g2, gear_idx)
    assert np.array_equal(m2, mini_idx)


def test_bulk_bitpack_decode_matches_scalar_helpers() -> None:
    from gear_optimizer.solver.solver_common import (
        gear_ids_from_code,
        gear_ids_from_codes,
        make_pack,
        mini_ids_from_code,
        mini_ids_from_codes,
    )

    gear_sizes = [3, 5, 2, 4, 6, 7]
    gear_pack = make_pack(gear_sizes)
    slot_item_ids = [np.asarray([(slot + 1) * 100 + idx for idx in range(size)], dtype=np.int32) for slot, size in enumerate(gear_sizes)]
    gear_codes = np.asarray(
        [
            sum((idx % size) << shift for idx, (size, shift) in enumerate(zip(gear_sizes, gear_pack.shifts, strict=True))),
            sum(((size - 1) << shift) for size, shift in zip(gear_sizes, gear_pack.shifts, strict=True)),
            0,
        ],
        dtype=np.uint64,
    )

    expected_gear = np.vstack(
        [gear_ids_from_code(int(code), pack=gear_pack, slot_item_ids=slot_item_ids) for code in gear_codes]
    )
    assert np.array_equal(
        gear_ids_from_codes(gear_codes, pack=gear_pack, slot_item_ids=slot_item_ids),
        expected_gear,
    )

    mini_sizes = [5, 5, 5]
    mini_pack = make_pack(mini_sizes)
    mini_item_ids = np.asarray([900 + idx for idx in range(5)], dtype=np.int32)
    mini_codes = np.asarray(
        [
            (1 << mini_pack.shifts[0]) | (2 << mini_pack.shifts[1]) | (3 << mini_pack.shifts[2]),
            (4 << mini_pack.shifts[0]) | (0 << mini_pack.shifts[1]) | (2 << mini_pack.shifts[2]),
        ],
        dtype=np.uint64,
    )

    expected_mini = np.vstack(
        [mini_ids_from_code(int(code), pack=mini_pack, mini_item_ids=mini_item_ids) for code in mini_codes]
    )
    assert np.array_equal(
        mini_ids_from_codes(mini_codes, pack=mini_pack, mini_item_ids=mini_item_ids),
        expected_mini,
    )


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


def test_mini_skyline_rejects_nonzero_mini_perfect_points_until_state_tracks_pp() -> None:
    from gear_optimizer.solver.mini_skyline import mini_combo_skyline
    from gear_optimizer.solver.solver_common import make_pack

    mini_pool = [
        {"Name": "pp-mini", "Perfect Points": 1},
        {"Name": "plain-a"},
        {"Name": "plain-b"},
    ]

    with pytest.raises(ValueError, match="requires zero mini Perfect Points"):
        mini_combo_skyline(
            mini_pool,
            p_color="Rush",
            s_color="",
            pack=make_pack([len(mini_pool), len(mini_pool), len(mini_pool)]),
        )


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


def test_local_mini_pair_filter_removes_only_disallowed_gear_cell_pairs() -> None:
    from tests.parity.exact_skyline import _apply_local_mini_pair_filter

    gear_idx, mini_idx, pruned = _apply_local_mini_pair_filter(
        pair_g_idx=np.asarray([0, 0, 1, 1], dtype=np.int32),
        pair_m_idx=np.asarray([0, 1, 0, 1], dtype=np.int32),
        mini_allowed_by_gear_cell=np.asarray([[True, False], [True, True]], dtype=np.bool_),
        mini_allowed_gear_rows=np.asarray([0, 1], dtype=np.int32),
    )

    assert pruned == 1
    assert list(zip(gear_idx.tolist(), mini_idx.tolist(), strict=True)) == [(0, 0), (1, 0), (1, 1)]
