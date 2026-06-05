"""Shared host-side helpers for GA and skyline operations."""

from __future__ import annotations

import hashlib

import numpy as np


def compute_array_sig(*arrays: np.ndarray) -> bytes:
    """Compute stable hash signature for numpy arrays."""
    h = hashlib.blake2b(digest_size=16)
    for arr in arrays:
        arr = np.ascontiguousarray(arr)
        h.update(arr.dtype.str.encode("utf-8"))
        h.update(np.array(arr.shape, dtype=np.int64).tobytes())
        h.update(arr.tobytes())
    return h.digest()


def probability_to_u32_fp(value: float) -> np.uint32:
    rate = float(value)
    if rate <= 0.0:
        return np.uint32(0)
    if rate >= 1.0:
        return np.uint32(0xFFFFFFFF)
    return np.uint32(int(rate * 4294967295.0))
