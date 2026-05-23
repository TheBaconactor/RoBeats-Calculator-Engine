import numpy as np

from gear_optimizer.solver.gear_skyline_gpu import _flatten_points, _flatten_states


def test_array_handoff_matches_legacy_state_flattening():
    states = {
        (0, 1, 0, 2): [(3, 7, 113)],
        (1, 2, 3, 4): [(5, 10, 111), (6, 12, 112)],
    }
    points = np.asarray(
        [
            [0, 1, 0, 2, 3, 7],
            [1, 2, 3, 4, 5, 10],
            [1, 2, 3, 4, 6, 12],
        ],
        dtype=np.int32,
    )
    codes = np.asarray([113, 111, 112], dtype=np.uint64)

    legacy = _flatten_states(states)
    array_native = _flatten_points(points, codes)

    for expected, actual in zip(legacy, array_native, strict=True):
        if isinstance(expected, np.ndarray):
            np.testing.assert_array_equal(actual, expected)
        else:
            assert actual == expected
