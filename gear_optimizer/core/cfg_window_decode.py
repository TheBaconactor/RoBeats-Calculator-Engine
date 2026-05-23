from __future__ import annotations

from typing import Any
import logging

import numpy as np

from gear_optimizer.core.constants import FG_PLATEAU_REP_STRIDE



logger = logging.getLogger(__name__)
def _rep_mask_width(n_sections: int) -> int:
    return min(max(int(n_sections), 0), 4)


def decode_cfg_counts_from_windows(cfg_idx: Any, cfg_windows: list[dict], n_sections: int):
    """
    Decode packed `cfg_idx` values into per-section FP targets using window metadata.

    Returns a numpy int32 array of shape (n_out, n_sections), or None if decoding
    is not possible.
    """
    if cfg_idx is None or cfg_windows is None or len(cfg_windows) == 0:
        return None

    try:
        n_sections_i = int(n_sections)
    except Exception as e:
        logger.debug(f"cfg_window_decode:decode_cfg_counts_from_windows: {e}")
        return None
    if n_sections_i <= 0:
        return None
    for window in cfg_windows:
        if isinstance(window, dict) and (str(window.get("kind") or "") == "list" or "counts_list" in window):
            raise ValueError("legacy FG counts_list config windows are not supported")

    try:
        cfg_idx_np = np.asarray(cfg_idx, dtype=np.int32)
    except Exception as e:
        logger.debug(f"cfg_window_decode:decode_cfg_counts_from_windows: {e}")
        return None

    try:
        n_out = int(cfg_idx_np.shape[0])
    except Exception as e:
        logger.debug(f"cfg_window_decode:decode_cfg_counts_from_windows: {e}")
        return None
    if n_out <= 0:
        return None

    try:
        cfg_counts = np.zeros((n_out, n_sections_i), dtype=np.int32)
        bases = [int(w.get("base", 0) or 0) for w in cfg_windows]
        lens = [int(w.get("len", 0) or 0) for w in cfg_windows]
        ends = [base + length for base, length in zip(bases, lens)]

        for gi in range(n_out):
            x = int(cfg_idx_np[gi])
            window_index = -1
            for wi, (b, e) in enumerate(zip(bases, ends)):
                if int(b) <= x < int(e):
                    window_index = wi
                    break
            if window_index < 0:
                continue

            w = cfg_windows[window_index]
            base = int(w.get("base", 0) or 0)
            local = int(x - base)
            rep_bits = _rep_mask_width(n_sections_i)
            rep_mask = int(local & ((1 << rep_bits) - 1)) if rep_bits > 0 else 0
            base_local = int(local >> rep_bits)
            max_fp_vec = list(w.get("max_fp") or [])
            rem = int(base_local)
            for s in range(n_sections_i - 1, -1, -1):
                basev = int(max(0, int(max_fp_vec[s] if s < len(max_fp_vec) else 0))) + 1
                if basev <= 0:
                    basev = 1
                val = rem % basev
                rem //= basev
                if s < rep_bits and ((rep_mask >> s) & 1) != 0:
                    val += int(FG_PLATEAU_REP_STRIDE)
                cfg_counts[gi, s] = int(val)

        return cfg_counts
    except Exception as e:
        logger.debug(f"cfg_window_decode:decode_cfg_counts_from_windows: {e}")
        return None
