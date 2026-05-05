import numpy as np

from gear_optimizer.core.cfg_window_decode import decode_cfg_counts_from_windows
from gear_optimizer.helpers.song_helpers.force_greats import decode_cfg_counts_from_windows as legacy_decode


def test_decode_cfg_counts_from_windows_core_and_legacy_imports_match():
    cfg_windows = [
        {"base": 0, "len": 4, "kind": "packed", "max_fp": [1, 2]},
        {"base": 4, "len": 2, "kind": "list", "counts_list": [[7, 8], [9, 10]]},
    ]

    cfg_idx = np.array([1, 4, 5], dtype=np.int32)

    core_counts = decode_cfg_counts_from_windows(cfg_idx, cfg_windows, 2)
    legacy_counts = legacy_decode(cfg_idx, cfg_windows, 2)

    expected = np.array([[0, 1], [7, 8], [9, 10]], dtype=np.int32)

    assert core_counts is not None
    assert legacy_counts is not None
    assert np.array_equal(core_counts, expected)
    assert np.array_equal(legacy_counts, expected)
