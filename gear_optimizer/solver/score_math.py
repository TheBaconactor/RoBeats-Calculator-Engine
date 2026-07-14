"""
Core scoring computation layer.

This module contains the "Compute Layer" - pure math functions that can be
ported to GPU (Taichi). These functions perform:
- Reference array lookups
- Score calculations
- Greedy gem optimization

GPU port only needs to reimplement these functions in Taichi.
"""

import numpy as np

from ..core.jit_setup import jit
from ..core.constants import (
    TOTAL_ROWS,
)


def lookup_reference_py(value, ref_array, total_rows=TOTAL_ROWS):
    """
    Python implementation of reference lookup.
    Clamps value to valid range and returns corresponding reference value.
    """
    clamped = max(0, min(total_rows, int(value)))
    return ref_array[clamped]


@jit(nopython=True, cache=True)
def fast_calculate_score(
    base_value,
    combo_mul,
    fever_mul,
    fever_mask_head,
    count_body_fever,
    count_body_normal,
):
    """
    Fast JIT-compiled score calculation.

    NOTE: The old fever_activations_count adjustment has been REMOVED.
    The timeline calculation now correctly handles note allocation per fever cycle,
    so no adjustment is needed.

    Args:
        base_value: Base score value per note
        combo_mul: Combo multiplier
        fever_mul: Fever multiplier
        fever_mask_head: Boolean array marking fever notes in head (first 100)
        count_body_fever: Number of fever notes after head
        count_body_normal: Number of normal notes after head

    Returns:
        int: Total calculated score
    """
    # Force float32 math so CPU and GPU paths share identical numeric behavior.
    # This significantly reduces divergence from float64 boundary rounding.
    base_f = np.float32(base_value)
    combo_mul_f = np.float32(combo_mul)
    fever_mul_f = np.float32(fever_mul)

    # floor(x) for positive x is equivalent to int(x) truncation.
    combo_val_per_note = int(base_f * combo_mul_f)
    fever_val_per_note = int(base_f * combo_mul_f * fever_mul_f)

    body_score = (count_body_fever * fever_val_per_note) + (count_body_normal * combo_val_per_note)

    factor = (combo_mul_f - np.float32(1.0)) * base_f / np.float32(100.0)
    total_head = 0
    n_head = len(fever_mask_head)

    for i in range(n_head):
        current_ramp_val = base_f + (np.float32(i + 1) * factor)
        if fever_mask_head[i]:
            val = int(current_ramp_val * fever_mul_f)
        else:
            val = int(current_ramp_val)
        total_head += val

    return int(body_score + total_head)
