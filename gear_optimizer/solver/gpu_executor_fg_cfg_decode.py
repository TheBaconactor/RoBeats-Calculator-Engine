from __future__ import annotations

import logging
from typing import Any

from gear_optimizer.core.cfg_window_decode import decode_cfg_counts_from_windows

logger = logging.getLogger(__name__)


def decode_cfg_counts_from_windows_for_gpu(cfg_idx: Any, cfg_windows: list[dict], n_sections: int) -> Any:
    return decode_cfg_counts_from_windows(cfg_idx, cfg_windows, n_sections)


def decode_cfg_counts_from_max_fp_matrix(
    cfg_idx: Any,
    ft_vals: Any,
    ff_vals: Any,
    max_fp_matrix: Any,
    ftff_pairs: Any,
    n_sections: int,
) -> Any:
    import numpy as np

    if cfg_idx is None or max_fp_matrix is None or ft_vals is None or ff_vals is None:
        return None
    try:
        n_sections_i = int(n_sections)
    except (ValueError, TypeError):
        return None
    if n_sections_i <= 0:
        return None

    try:
        cfg_idx_np = np.asarray(cfg_idx, dtype=np.int64)
        ft_np = np.asarray(ft_vals, dtype=np.int32)
        ff_np = np.asarray(ff_vals, dtype=np.int32)
    except Exception as e:
        logger.debug(f"gpu_executor_fg_cfg_decode:decode_cfg_counts_from_max_fp_matrix: {e}")
        return None
    if cfg_idx_np.shape[0] != ft_np.shape[0] or cfg_idx_np.shape[0] != ff_np.shape[0]:
        return None

    try:
        pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
    except Exception as e:
        logger.debug(f"gpu_executor_fg_cfg_decode:decode_cfg_counts_from_max_fp_matrix: {e}")
        return None
    if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
        return None

    try:
        max_fp_arr = np.asarray(max_fp_matrix, dtype=np.int32)
    except Exception as e:
        logger.debug(f"gpu_executor_fg_cfg_decode:decode_cfg_counts_from_max_fp_matrix: {e}")
        return None
    if max_fp_arr.ndim != 2 or int(max_fp_arr.shape[0]) != int(pairs_arr.shape[0]):
        return None

    try:
        pair_index: dict[tuple[int, int], int] = {}
        for i in range(int(pairs_arr.shape[0])):
            ft_i = int(pairs_arr[i, 0])
            ff_i = int(pairs_arr[i, 1])
            pair_index[(ft_i, ff_i)] = int(i)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None

    n_out = int(cfg_idx_np.shape[0])
    cfg_counts = np.zeros((int(n_out), int(n_sections_i)), dtype=np.int32)
    for gi in range(int(n_out)):
        row = pair_index.get((int(ft_np[gi]), int(ff_np[gi])), -1)
        if row < 0:
            continue
        idx = int(cfg_idx_np[gi])
        if idx < 0:
            continue
        try:
            max_fp_row = max_fp_arr[row]
        except Exception as e:
            logger.debug(f"gpu_executor_fg_cfg_decode:decode_cfg_counts_from_max_fp_matrix: {e}")
            continue
        for s in range(int(n_sections_i) - 1, -1, -1):
            try:
                basev = int(max(0, int(max_fp_row[s] if s < len(max_fp_row) else 0))) + 1
            except (ValueError, TypeError, IndexError):
                basev = 1
            if basev <= 0:
                basev = 1
            val = idx % basev
            idx //= basev
            cfg_counts[gi, s] = int(val)
    return cfg_counts
