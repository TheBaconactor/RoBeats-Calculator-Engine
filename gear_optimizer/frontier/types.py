from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NamedTuple

import numpy as np


class FgResponseSurface(NamedTuple):
    fever0: int
    fever1: int
    fever2: int
    fever3: int
    great0: int
    great1: int
    great2: int
    great3: int
    body_fever: int
    body_great: int
    body_fever_great: int = 0


@dataclass(frozen=True, slots=True)
class FgResponseFrontierResult:
    first_frontier: Any  # producer_surfaces.SurfaceRowsFirstFrontier
    states_evaluated: int
    actions: int
    transitions_evaluated: int
    generated_surfaces: int
    retained_surfaces_total: int
    max_state_frontier: int
    non_fever_base: int


@dataclass(frozen=True, slots=True)
class FgResponseFrontierSolveResult:
    best_score: int
    ft: int
    ff: int
    gem_counts: dict[str, int]
    stats: dict[str, Any]
    surface: FgResponseSurface
    non_fever_base: int
    raw_fever_fill: float
    real_fever_time: float


@dataclass(frozen=True, slots=True)
class SurfacePool:
    """The surfaces a gem search scores. Frontier f holds rows frontier_offsets[f] .. frontier_offsets[f] +
    frontier_lengths[f]; row r is head pattern pattern_ids[r] (pattern_words: its 4 fever and 4 Great words over the
    head notes; head_coeffs: its surface_head_coeffs; head_greats: its surface_head_greats) with body counts counts[r]
    (fever notes, Great notes, both)."""

    frontier_offsets: np.ndarray
    frontier_lengths: np.ndarray
    pattern_ids: np.ndarray
    pattern_words: np.ndarray
    counts: np.ndarray
    head_coeffs: np.ndarray
    head_greats: np.ndarray

