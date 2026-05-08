"""Canonical ref-array helpers for search and replay paths.

The optimizer's search path is allowed to use `float32` for GPU parity/perf,
while authoritative replay/persistence must use `float64` so exact rescoring
does not inherit GPU boundary drift.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Mapping
from typing import Any

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
_EXACT_REPLAY_REF_ARRAYS_LOCK = threading.Lock()
_EXACT_REPLAY_REF_ARRAYS_CACHE: dict[str, np.ndarray] | None = None


def build_ref_arrays_from_stats(stats_table, *, dtype=np.float64) -> dict[str, np.ndarray]:
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
        ref_arrays[name] = np.array(values, dtype=dtype)
    return ref_arrays


def _is_exact_replay_ref_arrays(ref_arrays: Any) -> bool:
    if not isinstance(ref_arrays, Mapping) or not ref_arrays:
        return False
    for name in _STAT_NAMES:
        arr = ref_arrays.get(name)
        if arr is None:
            return False
        try:
            arr_dtype = np.asarray(arr).dtype
        except (TypeError, ValueError) as e:
            logger.debug(f"ref_array_builder:_is_exact_replay_ref_arrays: {e}")
            return False
        if arr_dtype != np.float64:
            return False
    return True


def get_exact_replay_ref_arrays_cached() -> dict[str, np.ndarray] | None:
    global _EXACT_REPLAY_REF_ARRAYS_CACHE

    with _EXACT_REPLAY_REF_ARRAYS_LOCK:
        cached = _EXACT_REPLAY_REF_ARRAYS_CACHE
        if _is_exact_replay_ref_arrays(cached):
            return cached

        try:
            from gear_optimizer.core.config import load_paths_cache
            from gear_optimizer.core.constants import PATHS
            from gear_optimizer.data.csv_parser import read_table

            paths = load_paths_cache() or {}
            stats_path = str((paths.get("Stats") or PATHS.stats_csv) or "").strip()
            if not stats_path:
                return None
            stats_table = read_table(stats_path)
            built = build_ref_arrays_from_stats(stats_table, dtype=np.float64)
            if built:
                _EXACT_REPLAY_REF_ARRAYS_CACHE = built
            return _EXACT_REPLAY_REF_ARRAYS_CACHE
        except Exception as e:
            logger.debug(f"ref_array_builder:get_exact_replay_ref_arrays_cached: {e}")
            return cached if _is_exact_replay_ref_arrays(cached) else None


def resolve_exact_replay_ref_arrays(ref_arrays: Any) -> Any:
    if _is_exact_replay_ref_arrays(ref_arrays):
        return ref_arrays
    cached = get_exact_replay_ref_arrays_cached()
    if _is_exact_replay_ref_arrays(cached):
        return cached
    return ref_arrays
