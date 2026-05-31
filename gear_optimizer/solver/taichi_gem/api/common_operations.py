"""Shared host-side helpers for GA and skyline operations."""

from __future__ import annotations

import hashlib
from typing import Any

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


def upload_island_elites(
    fields_module: Any,
    elite_indices: np.ndarray,
    n_elites: int,
    cache_key: tuple[int, ...] | None,
    upload_buffer: np.ndarray | None,
) -> tuple[tuple[int, ...] | None, np.ndarray | None]:
    n_elites = int(n_elites)
    if n_elites <= 0:
        return cache_key, upload_buffer
    elite_arr = np.asarray(elite_indices[:n_elites], dtype=np.int32)
    key = tuple(int(x) for x in elite_arr.tolist())
    if cache_key == key:
        return cache_key, upload_buffer
    buf = upload_buffer
    if buf is None or int(buf.shape[0]) != int(fields_module.MAX_GENOMES):
        buf = np.zeros((fields_module.MAX_GENOMES,), dtype=np.int32)
    buf[:n_elites] = elite_arr
    if n_elites < int(fields_module.MAX_GENOMES):
        buf[n_elites:] = 0
    fields_module.island_elite_indices.from_numpy(buf)
    return key, buf
