"""
Stable array content signatures.

Used for cache keys that must survive process transport (pickling) and should not
depend on object identity.
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np


def array_sig16(v: Any) -> bytes:
    """
    Return a stable 16-byte content signature for a numpy-like array.

    Notes
    - Includes dtype/ndim/shape in the hash to avoid collisions between arrays with
      identical raw bytes but different interpretation.
    - Forces C-contiguity so views hash deterministically.
    """

    if v is None:
        return b"\x00"
    try:
        arr = np.asarray(v)
    except (TypeError, ValueError):
        return bytes(repr(v), "utf-8")
    if arr.ndim == 0:
        try:
            arr = np.asarray([arr.item()], dtype=arr.dtype)
        except (TypeError, ValueError):
            arr = np.asarray([repr(arr)], dtype=np.uint8)

    try:
        is_contig = bool(arr.flags["C_CONTIGUOUS"])
    except (AttributeError, KeyError, TypeError, ValueError):
        is_contig = False
    arr_c = arr if is_contig else np.ascontiguousarray(arr)

    h = hashlib.blake2b(digest_size=16)
    h.update(str(arr_c.dtype).encode("utf-8"))
    h.update(int(arr_c.ndim).to_bytes(1, "little", signed=False))
    for d in arr_c.shape:
        h.update(int(d).to_bytes(4, "little", signed=False))
    h.update(memoryview(arr_c).cast("B"))
    return h.digest()


def arrays_sig16(*values: Any) -> bytes:
    """Return a stable 16-byte content signature for a sequence of arrays."""

    h = hashlib.blake2b(digest_size=16)
    for value in values:
        h.update(array_sig16(value))
    return h.digest()
