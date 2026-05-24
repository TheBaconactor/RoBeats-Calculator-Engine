from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NamedTuple


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


@dataclass(frozen=True, slots=True)
class FgResponseFrontierResult:
    first_frontier: tuple[FgResponseSurface, ...]
    state_frontiers: dict[int, tuple[FgResponseSurface, ...]]
    states_evaluated: int
    actions: int
    transitions_evaluated: int
    generated_surfaces: int
    retained_surfaces_total: int
    max_state_frontier: int
    non_fever_base: int
    seconds: float


@dataclass(frozen=True, slots=True)
class FgResponseInnerResult:
    best_score: int
    surface_index: int
    g_pp: int
    g_cm: int
    g_fm: int
    g_ov: int
    final_pp: int
    final_cm: int
    final_fm: int
    final_primary: int
    final_secondary: int


@dataclass(frozen=True, slots=True)
class FgResponseFrontierSolveResult:
    best_score: int
    ft: int
    ff: int
    gem_counts: dict[str, int]
    stats: dict[str, Any]
    surface: FgResponseSurface
    frontier: FgResponseFrontierResult
    inner: FgResponseInnerResult
    seconds: float
    forced_counts: tuple[int, ...] = ()
    raw_fever_fill: float = 0.0
    real_fever_time: float = 0.0


_EMPTY_SURFACE = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
