"""GPU owner kernel entrypoints for FG response-frontier scoring."""

from __future__ import annotations

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
        from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import _score_response_group_meta_gpu

        rows, _logical_surface_rows = _score_response_group_meta_gpu(
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
        return rows

    @staticmethod
    def score_batch_on_owner(batch: Any) -> Any:
        from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
            score_prepared_force_greats_response_frontier_batch_on_gpu_owner,
        )

        return score_prepared_force_greats_response_frontier_batch_on_gpu_owner(batch)

    @staticmethod
    def materialize_owner_result(
        owner_result: Any,
        *,
        include_forced_counts: bool = False,
    ) -> list[Any]:
        from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
            materialize_force_greats_response_frontier_owner_result,
        )

        return materialize_force_greats_response_frontier_owner_result(
            owner_result,
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
