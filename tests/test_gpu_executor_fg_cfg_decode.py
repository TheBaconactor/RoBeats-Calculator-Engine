import numpy as np

from gear_optimizer.core.cfg_window_decode import decode_cfg_counts_from_windows
from gear_optimizer.solver.gpu_executor_fg import decode_cfg_counts_from_windows_for_gpu


def test_decode_cfg_counts_from_windows_for_gpu_delegates_to_core_decode():
    cfg_windows = [{"base": 0, "len": 24, "kind": "list", "counts_list": [(7, 8)]}]

    out = decode_cfg_counts_from_windows_for_gpu(np.array([0]), cfg_windows, 2)

    assert np.array_equal(out, decode_cfg_counts_from_windows(np.array([0]), cfg_windows, 2))
