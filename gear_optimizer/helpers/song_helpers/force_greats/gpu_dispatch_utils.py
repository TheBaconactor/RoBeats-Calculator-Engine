from __future__ import annotations

from typing import Any

import numpy as np


def safe_metric_count(items: Any) -> int:
    if items is None:
        return 0
    try:
        shape = getattr(items, "shape", None)
        if shape is not None and len(shape) > 0:
            return max(0, int(shape[0]))
    except (KeyError, TypeError, ValueError, AttributeError):
        pass
    try:
        return max(0, int(len(items)))
    except (ValueError, TypeError):
        return 0


def iter_ftff_chunks(pairs: Any, chunk_size: int):
    chunk_size = int(chunk_size)
    if chunk_size <= 0:
        yield pairs
        return
    if len(pairs) <= chunk_size:
        yield pairs
        return
    for i in range(0, len(pairs), chunk_size):
        yield pairs[i : i + chunk_size]


def pack_pairs_int32(pairs: Any):
    """
    Normalize pair collections as contiguous (n, 2) int32 arrays.

    Returns None when packing fails or shape is invalid.
    """
    if pairs is None:
        return None
    try:
        arr = np.asarray(pairs, dtype=np.int32)
        if arr.ndim != 2:
            arr = np.asarray(list(pairs), dtype=np.int32)
        if arr.ndim != 2 or int(arr.shape[1]) < 2:
            return None
        if int(arr.shape[1]) != 2:
            arr = arr[:, :2]
        if not arr.flags["C_CONTIGUOUS"]:
            arr = np.ascontiguousarray(arr)
        return arr
    except (ValueError, TypeError, KeyError):
        return None


__all__ = [
    "iter_ftff_chunks",
    "pack_pairs_int32",
    "safe_metric_count",
]
