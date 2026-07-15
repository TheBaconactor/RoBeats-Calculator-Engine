"""Shared host-side helpers for exact candidate operations."""

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
