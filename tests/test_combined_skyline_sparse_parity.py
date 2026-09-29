import numpy as np
import pytest


pytestmark = [pytest.mark.gpu]


def test_sparse_keeps_different_ff_timing_cells():
    from tests.parity.combined_skyline_sparse import combined_global_skyline_pairs_6d_sparse

    gear_points = np.asarray(
        [
            [0, 0, 0, 0, 0, 100],
            [0, 0, 0, 0, 10, 100],
        ],
        dtype=np.int32,
    )
    mini_points = np.asarray([[0, 0, 0, 0, 0]], dtype=np.int32)

    sparse_g, sparse_m = combined_global_skyline_pairs_6d_sparse(gear_points, mini_points)

    assert {(int(g), int(m)) for g, m in zip(sparse_g.tolist(), sparse_m.tolist(), strict=True)} == {
        (0, 0),
        (1, 0),
    }


def test_sparse_empty_inputs():
    from tests.parity.combined_skyline_sparse import combined_global_skyline_pairs_6d_sparse

    g, m = combined_global_skyline_pairs_6d_sparse(np.zeros((0, 6), dtype=np.int32), np.zeros((0, 5), dtype=np.int32))
    assert g.size == 0
    assert m.size == 0

    gp = np.asarray([[0, 1, 2, 3, 4, 100]], dtype=np.int32)
    g, m = combined_global_skyline_pairs_6d_sparse(gp, np.zeros((0, 5), dtype=np.int32))
    assert g.size == 0
    assert m.size == 0
