"""
Timestamp quantization helpers.

We keep these utilities NumPy-only and float32-first so both CPU and GPU paths
share consistent rounding behavior.
"""

from __future__ import annotations

import numpy as np


def quantize_to_int_ms(timestamps_sec: np.ndarray, *, snap_tol_ms: float = 0.1) -> np.ndarray:
    """
    Quantize seconds timestamps to integer milliseconds.

    RoBeats timing uses integer millisecond boundaries (floor(audio_time_ms) on
    server). Song dumps are effectively ms-quantized, but float32 math can land
    slightly below an integer boundary (e.g., 241.0ms -> 240.99999ms), which
    would produce an off-by-1 when flooring.

    We therefore snap values that are "very close" to an integer (within
    snap_tol_ms) to that integer; otherwise we fall back to floor semantics.

    Args:
        timestamps_sec: 1D sequence of timestamps in seconds.
        snap_tol_ms: Snap-to-integer tolerance in milliseconds.

    Returns:
        np.ndarray[int32]: quantized timestamps in milliseconds.
    """
    ts = np.asarray(timestamps_sec, dtype=np.float32)
    ms = ts * np.float32(1000.0)

    rounded = np.rint(ms)
    diff = np.abs(ms - rounded)
    tol = np.float32(snap_tol_ms)

    snapped = np.where(diff <= tol, rounded, np.floor(ms))
    return snapped.astype(np.int32, copy=False)

