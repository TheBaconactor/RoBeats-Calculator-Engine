"""
Shared numeric helpers for consistent flooring semantics across CPU, Numba, and Taichi code.
"""
from __future__ import annotations

from math import floor

import taichi as ti

from .jit_setup import jit

# Tiny epsilon to stabilize floor rounding across implementations.
FLOORING_EPSILON = 1e-5


def floor_eps(x: float, eps: float = FLOORING_EPSILON) -> float:
    """Floor with a small epsilon to reduce boundary rounding issues."""
    return floor(x + eps)


@jit(nopython=True, cache=True)
def floor_eps_nb(x):
    """Numba-friendly floor with epsilon."""
    return floor(x + FLOORING_EPSILON)


@ti.func
def ti_floor_eps(x):
    """Taichi-friendly floor with epsilon."""
    return ti.floor(x + FLOORING_EPSILON)


