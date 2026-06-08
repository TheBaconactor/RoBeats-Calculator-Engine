"""GPU owner kernel entrypoints for FG response-frontier scoring."""

from __future__ import annotations

import time
from typing import Any

import numpy as np


class GpuResponseKernelRunner:
    @staticmethod
    def build_group_rows_on_owner(batch: Any) -> Any:
        from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
            build_prepared_force_greats_response_frontier_group_arrays_on_owner,
        )

        return build_prepared_force_greats_response_frontier_group_arrays_on_owner(batch)

    @staticmethod
    def score_group_meta(
        *,
        group_meta: np.ndarray,
        group_offsets: np.ndarray,
        group_lengths: np.ndarray,
        primary_color: str,
        secondary_color: str,
        selected_color: str,
        ref_arrays: dict[str, Any],
        surface_words: np.ndarray,
        surface_counts: np.ndarray,
        surface_head_coeffs: np.ndarray,
    ) -> np.ndarray:
        from gear_optimizer.solver.taichi_gem.force_greats import response_frontier as _response_frontier

        inner_rows, _logical_surface_rows = _response_frontier._score_response_group_meta_gpu(
            group_meta=group_meta,
            group_offsets=group_offsets,
            group_lengths=group_lengths,
            primary_color=primary_color,
            secondary_color=secondary_color,
            selected_color=selected_color,
            ref_arrays=ref_arrays,
            surface_words=surface_words,
            surface_counts=surface_counts,
            surface_head_coeffs=surface_head_coeffs,
        )
        return inner_rows

    @staticmethod
    def score_batch_on_owner(batch: Any) -> Any:
        from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import FgResponseFrontierOwnerResult

        built_batch = GpuResponseKernelRunner.build_group_rows_on_owner(batch)
        if built_batch.group_meta is None:
            raise RuntimeError("response frontier GPU owner scoring requires built group rows")
        surface_words = built_batch.scoring_surface_words
        surface_counts = built_batch.scoring_surface_counts
        surface_head_coeffs = built_batch.scoring_surface_head_coeffs
        group_offsets = built_batch.scoring_group_offsets
        group_lengths = built_batch.scoring_group_lengths
        if int(group_offsets.shape[0]) != int(built_batch.group_meta.shape[0]) or int(group_lengths.shape[0]) != int(
            built_batch.group_meta.shape[0]
        ):
            raise ValueError("response frontier prepared scoring arrays have inconsistent group lengths")
        if (
            int(surface_words.ndim) != 2
            or int(surface_words.shape[1]) != 8
            or int(surface_counts.ndim) != 2
            or int(surface_counts.shape[1]) != 3
            or int(surface_head_coeffs.ndim) != 2
            or int(surface_head_coeffs.shape[1]) != 4
        ):
            raise ValueError("response frontier prepared scoring arrays have invalid shape")
        inner_rows = GpuResponseKernelRunner.score_group_meta(
            group_meta=built_batch.group_meta,
            group_offsets=group_offsets,
            group_lengths=group_lengths,
            primary_color=built_batch.primary_color,
            secondary_color=built_batch.secondary_color,
            selected_color=built_batch.selected_color,
            ref_arrays=built_batch.ref_arrays,
            surface_words=surface_words,
            surface_counts=surface_counts,
            surface_head_coeffs=surface_head_coeffs,
        )
        if int(inner_rows.shape[0]) != int(built_batch.group_meta.shape[0]):
            raise ValueError("response frontier exact GPU batch returned the wrong number of group results")
        return FgResponseFrontierOwnerResult(
            batch=built_batch,
            inner_rows=np.asarray(inner_rows, dtype=np.int32),
        )

    @staticmethod
    def materialize_owner_result(
        owner_result: Any,
        *,
        include_forced_counts: bool = False,
    ) -> list[Any]:
        from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
            FgResponseFrontierOwnerResult,
            materialize_prepared_force_greats_response_frontier_batch_results,
        )

        if not isinstance(owner_result, FgResponseFrontierOwnerResult):
            raise RuntimeError("FG response frontier GPU owner returned an invalid owner result")
        return materialize_prepared_force_greats_response_frontier_batch_results(
            owner_result.batch,
            owner_result.inner_rows,
            include_forced_counts=bool(include_forced_counts),
        )

    @staticmethod
    def score_batch_sync(batch: Any, *, include_forced_counts: bool = False) -> list[Any]:
        from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
            score_prepared_force_greats_response_frontier_batch_sync,
        )

        return score_prepared_force_greats_response_frontier_batch_sync(
            batch,
            include_forced_counts=bool(include_forced_counts),
        )

    @staticmethod
    def run_batches_via_client(
        gpu_client: Any,
        batches: tuple[Any, ...] | list[Any],
        *,
        include_forced_counts: bool = False,
    ) -> list[tuple[list[Any], dict[str, float]]]:
        submitted: list[tuple[Any, dict[str, float]]] = []
        for batch in batches:
            timing: dict[str, float] = {}
            handle = gpu_client.submit_force_greats_response_frontier_score_batch(
                {
                    "batch": batch,
                    "timing": timing,
                }
            )
            submitted.append((handle, timing))

        prepared_results: list[tuple[list[Any], dict[str, float]]] = []
        for handle, timing in submitted:
            owner_result = handle.future.result()
            materialize_t0 = time.perf_counter()
            results = GpuResponseKernelRunner.materialize_owner_result(
                owner_result,
                include_forced_counts=bool(include_forced_counts),
            )
            timing["materialize_s"] = max(0.0, time.perf_counter() - float(materialize_t0))
            prepared_results.append((results, timing))
        return prepared_results
