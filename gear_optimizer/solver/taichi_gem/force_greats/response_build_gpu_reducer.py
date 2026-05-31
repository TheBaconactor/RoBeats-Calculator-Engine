from __future__ import annotations

import concurrent.futures
import os

import numpy as np

from .response_build_gpu_numba import _first_frontier_from_precomputed_end_indices_numba
from .response_build_gpu_surfaces import _surface_from_numba_row
from .response_types import FgResponseFrontierResult

_FIRST_ONLY_REDUCER_THREADS = max(1, min(int(os.cpu_count() or 1), 8))


def configure_force_greats_response_first_frontier_threads(max_threads: int) -> int:
    global _FIRST_ONLY_REDUCER_THREADS
    previous = int(_FIRST_ONLY_REDUCER_THREADS)
    _FIRST_ONLY_REDUCER_THREADS = max(1, min(int(max_threads), int(os.cpu_count() or 1), 8))
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
    later_fill: np.ndarray,
    first_fill: np.ndarray,
    later_forced: np.ndarray,
    first_forced: np.ndarray,
    timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    timestamp_end_idx: np.ndarray,
    great_end_idx: np.ndarray,
    real_time_idx: int,
    use_forced_great_timing: bool,
) -> FgResponseFrontierResult:
    first_rows, states_evaluated, generated_surfaces, retained_total, max_state_frontier = (
        _first_frontier_from_precomputed_end_indices_numba(
            int(n),
            int(action_count),
            later_fill,
            first_fill,
            later_forced,
            first_forced,
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            int(real_time_idx),
            1 if bool(use_forced_great_timing) else 0,
        )
    )
    return FgResponseFrontierResult(
        first_frontier=tuple(_surface_from_numba_row(first_rows[idx]) for idx in range(int(first_rows.shape[0]))),
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
    great_candidate_timestamps: np.ndarray,
    timestamp_end_idx: np.ndarray,
    great_end_idx: np.ndarray,
    real_time_index: np.ndarray,
    use_forced_great_timing: bool,
) -> list[tuple[int, FgResponseFrontierResult]]:
    results: list[tuple[int, FgResponseFrontierResult]] = []
    for local_idx in range(int(start), int(stop)):
        item = chunk[int(local_idx)]
        source_idx = int(item[0])
        results.append(
            (
                source_idx,
                _first_frontier_result_from_precomputed_end_indices(
                    n=int(n),
                    action_count=int(item[3].shape[0]),
                    non_fever_base=int(item[1]),
                    later_fill=np.ascontiguousarray(item[3], dtype=np.int32),
                    first_fill=np.ascontiguousarray(item[4], dtype=np.int32),
                    later_forced=np.ascontiguousarray(item[5], dtype=np.int32),
                    first_forced=np.ascontiguousarray(item[6], dtype=np.int32),
                    timestamps=timestamps,
                    great_candidate_timestamps=great_candidate_timestamps,
                    timestamp_end_idx=timestamp_end_idx,
                    great_end_idx=great_end_idx,
                    real_time_idx=int(real_time_index[int(local_idx)]),
                    use_forced_great_timing=bool(use_forced_great_timing),
                ),
            )
        )
    return results
