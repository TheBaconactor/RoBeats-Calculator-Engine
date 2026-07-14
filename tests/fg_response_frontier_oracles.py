"""Test-only reference helpers for the shared Base/FG response producer.

These helpers intentionally exercise production semantic primitives through slower,
geometry-at-a-time orchestration. They are differential oracles, never runtime routes.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
    _action_table,
    _build_activation_reachability_context,
    _edge_surface_options,
    _option_with_witness,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
    FgResponseFrontierResult,
    FgResponseSurface,
    _EMPTY_SURFACE,
)


def _combine_surfaces(edge: FgResponseSurface, tail: FgResponseSurface) -> FgResponseSurface:
    return FgResponseSurface(
        int(edge.fever0 | tail.fever0),
        int(edge.fever1 | tail.fever1),
        int(edge.fever2 | tail.fever2),
        int(edge.fever3 | tail.fever3),
        int(edge.great0 | tail.great0),
        int(edge.great1 | tail.great1),
        int(edge.great2 | tail.great2),
        int(edge.great3 | tail.great3),
        int(edge.body_fever + tail.body_fever),
        int(edge.body_great + tail.body_great),
        int(edge.body_fever_great + tail.body_fever_great),
    )


def _surface_dominates(left: FgResponseSurface, right: FgResponseSurface) -> bool:
    left_normal_great = int(left.body_great) - int(left.body_fever_great)
    right_normal_great = int(right.body_great) - int(right.body_fever_great)
    return (
        int(left.body_fever) >= int(right.body_fever)
        and int(left_normal_great) <= int(right_normal_great)
        and int(left.body_fever_great) <= int(right.body_fever_great)
        and (int(right.fever0) & ~int(left.fever0)) == 0
        and (int(right.fever1) & ~int(left.fever1)) == 0
        and (int(right.fever2) & ~int(left.fever2)) == 0
        and (int(right.fever3) & ~int(left.fever3)) == 0
        and (int(left.great0) & ~int(right.great0)) == 0
        and (int(left.great1) & ~int(right.great1)) == 0
        and (int(left.great2) & ~int(right.great2)) == 0
        and (int(left.great3) & ~int(right.great3)) == 0
        and (
            int(left.fever0 & left.great0),
            int(left.fever1 & left.great1),
            int(left.fever2 & left.great2),
            int(left.fever3 & left.great3),
        )
        == (
            int(right.fever0 & right.great0),
            int(right.fever1 & right.great1),
            int(right.fever2 & right.great2),
            int(right.fever3 & right.great3),
        )
    )


def _to_numba_surface(surface: FgResponseSurface) -> tuple[np.uint64, ...]:
    return (
        np.uint64(int(surface.fever0) | (int(surface.fever1) << 32)),
        np.uint64(int(surface.fever2) | (int(surface.fever3) << 32)),
        np.uint64(int(surface.great0) | (int(surface.great1) << 32)),
        np.uint64(int(surface.great2) | (int(surface.great3) << 32)),
        np.uint64(int(surface.body_fever)),
        np.uint64(int(surface.body_great)),
        np.uint64(int(surface.body_fever_great)),
    )


def _from_numba_surface(row) -> FgResponseSurface:
    fever_lo = int(row[0])
    fever_hi = int(row[1])
    great_lo = int(row[2])
    great_hi = int(row[3])
    return FgResponseSurface(
        fever_lo & 0xFFFFFFFF,
        (fever_lo >> 32) & 0xFFFFFFFF,
        fever_hi & 0xFFFFFFFF,
        (fever_hi >> 32) & 0xFFFFFFFF,
        great_lo & 0xFFFFFFFF,
        (great_lo >> 32) & 0xFFFFFFFF,
        great_hi & 0xFFFFFFFF,
        (great_hi >> 32) & 0xFFFFFFFF,
        int(row[4]),
        int(row[5]),
        int(row[6]),
    )


def _head_envelope_reduce_surfaces(
    surfaces: tuple[FgResponseSurface, ...],
    *,
    lo_pos: int,
    hi_pos: int,
) -> tuple[FgResponseSurface, ...]:
    if not surfaces:
        return (_EMPTY_SURFACE,)
    from numba.typed import List

    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _HEAD_FILTER_MIN_SURFACES,
        _NUMBA_SURFACE_TYPE,
        _numba_head_envelope_filter,
        _numba_reduce,
    )

    rows = List.empty_list(_NUMBA_SURFACE_TYPE)
    for surface in surfaces:
        rows.append(_to_numba_surface(surface))
    reduced = _numba_head_envelope_filter(
        _numba_reduce(rows),
        int(lo_pos),
        int(hi_pos),
        int(_HEAD_FILTER_MIN_SURFACES),
    )
    return tuple(_from_numba_surface(reduced[idx]) for idx in range(len(reduced))) or (
        _EMPTY_SURFACE,
    )


def _reduce_surfaces(
    surfaces: tuple[FgResponseSurface, ...],
    *,
    lo_pos: int = 0,
    hi_pos: int = 100,
) -> tuple[FgResponseSurface, ...]:
    if not surfaces:
        return (_EMPTY_SURFACE,)
    kept: list[FgResponseSurface] = []
    for surface in surfaces:
        if any(_surface_dominates(other, surface) for other in kept):
            continue
        kept = [other for other in kept if not _surface_dominates(surface, other)]
        if surface not in kept:
            kept.append(surface)
    reduced = tuple(kept) if kept else (_EMPTY_SURFACE,)
    if len(reduced) > 96 and int(hi_pos) > int(lo_pos):
        return _head_envelope_reduce_surfaces(reduced, lo_pos=int(lo_pos), hi_pos=int(hi_pos))
    return reduced


def edge_end_oracle(
    *,
    n: int,
    a: int,
    activation_great: bool,
    real_fever_time: float,
    use_forced_great_timing: bool,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray | None = None,
    great_candidate_timestamps: np.ndarray | None = None,
    perfect_floor_timestamps: np.ndarray,
) -> tuple[int, float, int]:
    """Plain-Python endpoint oracle for tests of precomputed producer end tables."""
    perfect_ts = timestamps if perfect_candidate_timestamps is None else perfect_candidate_timestamps
    great_ts = timestamps if great_candidate_timestamps is None else great_candidate_timestamps
    start_time = float(perfect_ts[int(a)])
    carry_idx = -1
    if bool(use_forced_great_timing) and bool(activation_great) and int(a) < int(n):
        activation_t = float(great_ts[int(a)])
        if activation_t > start_time:
            start_time = activation_t
            carry_idx = int(a)
    end = int(
        np.searchsorted(
            perfect_floor_timestamps,
            np.float32(start_time + float(real_fever_time)),
            side="left",
        )
    )
    end = max(int(end), int(a) + 1)
    return min(int(end), int(n)), float(start_time), int(carry_idx)


def edge_surface_option_details(
    *,
    i: int,
    first: bool,
    n: int,
    actions: list[int],
    later_fill: list[int],
    first_fill: list[int],
    later_forced: list[int],
    first_forced: list[int],
    real_fever_time: float,
    use_forced_great_timing: bool,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray | None = None,
    great_candidate_timestamps: np.ndarray | None = None,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    raw_fever_fill: float,
    lanes: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    """Materialize every option and witness for focused producer tests."""
    if lanes is None:
        raise ValueError("lanes are required for input-engine-aware response tests")
    reachability_context = _build_activation_reachability_context(
        timestamps=timestamps,
        perfect_floor_timestamps=perfect_floor_timestamps,
        perfect_candidate_timestamps=(
            timestamps if perfect_candidate_timestamps is None else perfect_candidate_timestamps
        ),
        great_floor_timestamps=great_floor_timestamps,
        great_candidate_timestamps=(
            timestamps if great_candidate_timestamps is None else great_candidate_timestamps
        ),
        lanes=lanes,
        fever_fill_denom=float(raw_fever_fill),
    )
    return [
        _option_with_witness(
            option,
            reachability_context=reachability_context,
            timestamps=timestamps,
            n=int(n),
            real_fever_time=float(real_fever_time),
            perfect_floor_timestamps=perfect_floor_timestamps,
        )
        for option in _edge_surface_options(
            reachability_context=reachability_context,
            i=int(i),
            first=bool(first),
            n=int(n),
            actions=actions,
            later_fill=later_fill,
            first_fill=first_fill,
            later_forced=later_forced,
            first_forced=first_forced,
            real_fever_time=float(real_fever_time),
            use_forced_great_timing=bool(use_forced_great_timing),
            timestamps=timestamps,
            perfect_candidate_timestamps=perfect_candidate_timestamps,
            great_candidate_timestamps=great_candidate_timestamps,
            perfect_floor_timestamps=perfect_floor_timestamps,
            great_floor_timestamps=great_floor_timestamps,
            lanes=lanes,
            raw_fever_fill=float(raw_fever_fill),
        )
    ]


def input_engine_rebuild_first_frontier(
    *,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    lanes: np.ndarray,
    raw_fever_fill: float,
    non_fever_base: int,
    real_fever_time: float,
    use_forced_great_timing: bool,
) -> FgResponseFrontierResult:
    """Slow exact recurrence used only to check the optimized Numba reducer."""
    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=float(raw_fever_fill),
        non_fever_base=max(0, int(non_fever_base)),
        use_forced_great_timing=bool(use_forced_great_timing),
    )
    n = int(timestamps.shape[0])
    reachability_context = _build_activation_reachability_context(
        timestamps=timestamps,
        perfect_floor_timestamps=perfect_floor_timestamps,
        perfect_candidate_timestamps=perfect_candidate_timestamps,
        great_floor_timestamps=great_floor_timestamps,
        great_candidate_timestamps=great_candidate_timestamps,
        lanes=lanes,
        fever_fill_denom=float(raw_fever_fill),
    )
    memo: dict[tuple[int, bool], tuple[FgResponseSurface, ...]] = {}
    states_evaluated = 0
    generated_surfaces = 0
    retained_surfaces_total = 0
    max_state_frontier = 1

    def _frontier(state: int, first: bool) -> tuple[FgResponseSurface, ...]:
        nonlocal states_evaluated, generated_surfaces, retained_surfaces_total, max_state_frontier
        if int(state) >= int(n):
            return (_EMPTY_SURFACE,)
        key = (int(state), bool(first))
        cached = memo.get(key)
        if cached is not None:
            return cached
        states_evaluated += 1
        generated: list[FgResponseSurface] = []
        for option in _edge_surface_options(
            reachability_context=reachability_context,
            i=int(state),
            first=bool(first),
            n=int(n),
            actions=actions,
            later_fill=later_fill,
            first_fill=first_fill,
            later_forced=later_forced,
            first_forced=first_forced,
            real_fever_time=float(real_fever_time),
            use_forced_great_timing=bool(use_forced_great_timing),
            timestamps=timestamps,
            perfect_candidate_timestamps=perfect_candidate_timestamps,
            great_candidate_timestamps=great_candidate_timestamps,
            perfect_floor_timestamps=perfect_floor_timestamps,
            great_floor_timestamps=great_floor_timestamps,
            lanes=lanes,
            raw_fever_fill=float(raw_fever_fill),
        ):
            edge = option["surface"]
            next_state = int(option["next_state"])
            if next_state <= int(state):
                raise ValueError("response test oracle emitted a non-advancing section")
            tails = (_EMPTY_SURFACE,) if next_state >= int(n) else _frontier(next_state, False)
            for tail in tails:
                generated.append(_combine_surfaces(edge, tail))
        generated_surfaces += len(generated)
        reduced = _reduce_surfaces(tuple(generated), lo_pos=int(state), hi_pos=min(int(n), 100))
        retained_surfaces_total += len(reduced)
        max_state_frontier = max(int(max_state_frontier), int(len(reduced)))
        memo[key] = reduced
        return reduced

    first_frontier = _frontier(0, True)
    return FgResponseFrontierResult(
        first_frontier=first_frontier,
        state_frontiers={},
        states_evaluated=int(states_evaluated),
        actions=int(len(actions)),
        transitions_evaluated=int(generated_surfaces),
        generated_surfaces=int(generated_surfaces),
        retained_surfaces_total=int(retained_surfaces_total),
        max_state_frontier=int(max_state_frontier),
        non_fever_base=int(non_fever_base),
        seconds=0.0,
    )
