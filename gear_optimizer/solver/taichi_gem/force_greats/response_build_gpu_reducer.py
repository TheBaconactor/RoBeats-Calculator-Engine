from __future__ import annotations

import concurrent.futures
import os

import numpy as np

from . import response_build_gpu_numba as _rb_numba
from .response_build_gpu_numba import _first_frontier_from_precomputed_end_indices_numba
from .response_build_gpu_surfaces import SurfaceRowsFirstFrontier
from .response_types import FgResponseFrontierResult

_FIRST_ONLY_REDUCER_THREADS = max(1, int(os.cpu_count() or 1))


def configure_force_greats_response_first_frontier_threads(max_threads: int) -> int:
    global _FIRST_ONLY_REDUCER_THREADS
    previous = int(_FIRST_ONLY_REDUCER_THREADS)
    _FIRST_ONLY_REDUCER_THREADS = max(1, min(int(max_threads), int(os.cpu_count() or 1)))
    return previous


def _resolve_first_only_reducer_threads(work_items: int) -> int:
    return max(1, min(int(work_items), int(_FIRST_ONLY_REDUCER_THREADS)))


def _first_frontier_reducer_executor(max_workers: int) -> concurrent.futures.ThreadPoolExecutor:
    return concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, int(max_workers)),
        thread_name_prefix="FGFirstFrontier",
    )


def _first_frontier_result_from_precomputed_end_indices(
    *,
    n: int,
    action_count: int,
    non_fever_base: int,
    raw_fever_fill: float,
    action_k: np.ndarray,
    later_fill: np.ndarray,
    first_fill: np.ndarray,
    later_forced: np.ndarray,
    first_forced: np.ndarray,
    later_activation_forced: np.ndarray,
    first_activation_forced: np.ndarray,
    timestamps: np.ndarray,
    candidate_high_delta_max: float,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    lanes: np.ndarray,
    prefix_perfect_hit: np.ndarray,
    prefix_perfect_valid: np.ndarray,
    prefix_late_hit: np.ndarray,
    prefix_late_valid: np.ndarray,
    timestamp_end_idx: np.ndarray,
    perfect_end_idx: np.ndarray,
    great_end_idx: np.ndarray,
    great_floor_end_idx: np.ndarray,
    capped_perfect_edge_e: np.ndarray,
    capped_late_edge_e: np.ndarray,
    capped_eg_perfect_e: np.ndarray,
    capped_eg_late_e: np.ndarray,
    real_fever_time: float,
    real_time_idx: int,
    use_forced_great_timing: bool,
    region_table: tuple,
) -> FgResponseFrontierResult:
    first_rows, states_evaluated, generated_surfaces, retained_total, max_state_frontier = (
        _first_frontier_from_precomputed_end_indices_numba(
            int(n),
            int(action_count),
            int(action_k.shape[0]),
            float(raw_fever_fill),
            action_k,
            later_fill,
            first_fill,
            later_forced,
            first_forced,
            later_activation_forced,
            first_activation_forced,
            timestamps,
            candidate_high_delta_max,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            perfect_floor_timestamps,
            great_floor_timestamps,
            lanes,
            prefix_perfect_hit,
            prefix_perfect_valid,
            prefix_late_hit,
            prefix_late_valid,
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            great_floor_end_idx,
            capped_perfect_edge_e,
            capped_late_edge_e,
            capped_eg_perfect_e,
            capped_eg_late_e,
            float(real_fever_time),
            int(real_time_idx),
            1 if bool(use_forced_great_timing) else 0,
            # Issue #44 Route A: head cone-dominance size gate, read LIVE from the module constant so
            # the losslessness verifiers (tools/verify/validate_cone_lossless.py, measure_cone_pareto.py)
            # can disable the prune via monkeypatch (no njit recompile) to recover the full reduce-only
            # frontier. Production always gets the default _HEAD_FILTER_MIN_SURFACES.
            int(_rb_numba._HEAD_FILTER_MIN_SURFACES),
            region_table[0],
            region_table[1],
            region_table[2],
            region_table[3],
            region_table[4],
            region_table[5],
            region_table[6],
            region_table[7],
        )
    )
    return FgResponseFrontierResult(
        first_frontier=SurfaceRowsFirstFrontier(first_rows),
        state_frontiers={},
        states_evaluated=int(states_evaluated),
        actions=int(action_count),
        transitions_evaluated=0,
        generated_surfaces=int(generated_surfaces),
        retained_surfaces_total=int(retained_total),
        max_state_frontier=int(max_state_frontier),
        non_fever_base=int(non_fever_base),
        seconds=0.0,
    )


def _first_frontier_results_for_precomputed_range(
    *,
    n: int,
    chunk: list[tuple],
    start: int,
    stop: int,
    timestamps: np.ndarray,
    candidate_high_delta_max: float,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    lanes: np.ndarray,
    prefix_perfect_hit: np.ndarray,
    prefix_perfect_valid: np.ndarray,
    prefix_late_hit: np.ndarray,
    prefix_late_valid: np.ndarray,
    timestamp_end_idx: np.ndarray,
    perfect_end_idx: np.ndarray,
    great_end_idx: np.ndarray,
    great_floor_end_idx: np.ndarray,
    capped_perfect_edge_e: np.ndarray,
    capped_late_edge_e: np.ndarray,
    capped_eg_perfect_e: np.ndarray,
    capped_eg_late_e: np.ndarray,
    real_time_index: np.ndarray,
    use_forced_great_timing: bool,
    region_tables_by_key: dict,
) -> list[tuple[int, FgResponseFrontierResult]]:
    results: list[tuple[int, FgResponseFrontierResult]] = []
    for local_idx in range(int(start), int(stop)):
        item = chunk[int(local_idx)]
        source_idx = int(item[0])
        region_table = region_tables_by_key[(float(item[2]), int(item[1]))]
        results.append(
            (
                source_idx,
                _first_frontier_result_from_precomputed_end_indices(
                    n=int(n),
                    action_count=int(item[5].shape[0]),
                    non_fever_base=int(item[1]),
                    raw_fever_fill=float(item[2]),
                    action_k=np.ascontiguousarray(item[4], dtype=np.int32),
                    later_fill=np.ascontiguousarray(item[5], dtype=np.int32),
                    first_fill=np.ascontiguousarray(item[6], dtype=np.int32),
                    later_forced=np.ascontiguousarray(item[7], dtype=np.int32),
                    first_forced=np.ascontiguousarray(item[8], dtype=np.int32),
                    later_activation_forced=np.ascontiguousarray(item[9], dtype=np.int32),
                    first_activation_forced=np.ascontiguousarray(item[10], dtype=np.int32),
                    timestamps=timestamps,
                    candidate_high_delta_max=candidate_high_delta_max,
                    perfect_candidate_timestamps=perfect_candidate_timestamps,
                    great_candidate_timestamps=great_candidate_timestamps,
                    perfect_floor_timestamps=perfect_floor_timestamps,
                    great_floor_timestamps=great_floor_timestamps,
                    lanes=lanes,
                    prefix_perfect_hit=prefix_perfect_hit,
                    prefix_perfect_valid=prefix_perfect_valid,
                    prefix_late_hit=prefix_late_hit,
                    prefix_late_valid=prefix_late_valid,
                    timestamp_end_idx=timestamp_end_idx,
                    perfect_end_idx=perfect_end_idx,
                    great_end_idx=great_end_idx,
                    great_floor_end_idx=great_floor_end_idx,
                    capped_perfect_edge_e=capped_perfect_edge_e,
                    capped_late_edge_e=capped_late_edge_e,
                    capped_eg_perfect_e=capped_eg_perfect_e,
                    capped_eg_late_e=capped_eg_late_e,
                    real_fever_time=float(item[3]),
                    real_time_idx=int(real_time_index[int(local_idx)]),
                    use_forced_great_timing=bool(use_forced_great_timing),
                    region_table=region_table,
                ),
            )
        )
    return results
