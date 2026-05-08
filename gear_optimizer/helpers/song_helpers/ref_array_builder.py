"""Canonical ref-array builder shared by app_async_db and drain_pending_fg_jobs.

Eliminates the duplicated _build_ref_arrays / _preload_ref_arrays functions
that previously lived independently in each module.
"""

from __future__ import annotations
import logging

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS



logger = logging.getLogger(__name__)
_STAT_NAMES = [
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Fill Rate",
    "Fever Time",
]


def build_ref_arrays_from_stats(stats_table) -> dict:
    ref_arrays: dict[str, np.ndarray] = {}
    for i, name in enumerate(_STAT_NAMES):
        values = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception as e:
                logger.debug(f"ref_array_builder:build_ref_arrays_from_stats: {e}")
                val = 0
            values.append(val)
        ref_arrays[name] = np.array(values, dtype=np.float64)
    return ref_arrays
