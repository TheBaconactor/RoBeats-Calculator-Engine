import numpy as np

from gear_optimizer.core.cfg_window_decode import decode_cfg_counts_from_windows
from gear_optimizer.solver.gpu_executor_fg import (
    decode_cfg_counts_from_max_fp_matrix,
    decode_cfg_counts_from_windows_for_gpu,
)


def test_decode_cfg_counts_from_max_fp_matrix_decodes_mixed_radix_counts():
    cfg_idx = np.array([20, 12], dtype=np.int32)
    ft_vals = np.array([1, 3], dtype=np.int32)
    ff_vals = np.array([2, 4], dtype=np.int32)
    ftff_pairs = np.array([[1, 2], [3, 4]], dtype=np.int32)
    max_fp_matrix = np.array([[1, 2], [0, 3]], dtype=np.int16)

    out = decode_cfg_counts_from_max_fp_matrix(
        cfg_idx,
        ft_vals,
        ff_vals,
        max_fp_matrix,
        ftff_pairs,
        n_sections=2,
    )

    assert np.array_equal(out, np.array([[1, 2], [0, 3]], dtype=np.int32))


def test_decode_cfg_counts_from_max_fp_matrix_returns_none_for_invalid_shapes():
    out = decode_cfg_counts_from_max_fp_matrix(
        cfg_idx=np.array([0, 1], dtype=np.int32),
        ft_vals=np.array([1], dtype=np.int32),
        ff_vals=np.array([2], dtype=np.int32),
        max_fp_matrix=np.array([[1, 2]], dtype=np.int16),
        ftff_pairs=np.array([[1, 2]], dtype=np.int32),
        n_sections=2,
    )

    assert out is None


def test_decode_cfg_counts_from_windows_for_gpu_delegates_to_core_decode():
    cfg_windows = [{"base": 0, "len": 24, "kind": "max_fp", "max_fp": [1, 2]}]

    out = decode_cfg_counts_from_windows_for_gpu(np.array([20]), cfg_windows, 2)

    assert np.array_equal(out, decode_cfg_counts_from_windows(np.array([20]), cfg_windows, 2))


def test_decode_cfg_counts_from_max_fp_matrix_handles_single_row():
    out = decode_cfg_counts_from_max_fp_matrix(
        np.array([20]),
        np.array([1]),
        np.array([2]),
        np.array([[1, 2]], dtype=np.int16),
        np.array([[1, 2]], dtype=np.int32),
        2,
    )

    assert np.array_equal(out, np.array([[1, 2]], dtype=np.int32))


def test_decode_cfg_counts_from_max_fp_matrix_preserves_plateau_rep_flags():
    out = decode_cfg_counts_from_max_fp_matrix(
        np.array([23]),
        np.array([1]),
        np.array([2]),
        np.array([[1, 2]], dtype=np.int16),
        np.array([[1, 2]], dtype=np.int32),
        2,
    )

    assert np.array_equal(out, np.array([[65, 66]], dtype=np.int32))
