from __future__ import annotations

from typing import Any

from gear_optimizer.solver.fg_response_scoring.gpu_kernel_runner import GpuResponseKernelRunner
from gear_optimizer.solver.fg_response_scoring.planner import FgResponseFrontierPreparedPlan
from gear_optimizer.solver.taichi_gem.force_greats import FgResponseFrontierSolveResult


class GpuScoreEngine:
    """Submit prepared FG response-frontier batches through the GPU owner queue."""

    @staticmethod
    def score_plan(
        plan: FgResponseFrontierPreparedPlan,
        *,
        gpu_client: Any | None,
        include_forced_counts: bool = False,
    ) -> tuple[list[list[FgResponseFrontierSolveResult]], list[dict[str, float]]]:
        from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
            run_prepared_force_greats_response_frontier_batches_via_client,
        )

        batches = [prepared.batch for prepared in plan.prepared_batches]
        if gpu_client is not None:
            handles = run_prepared_force_greats_response_frontier_batches_via_client(
                gpu_client,
                batches,
                include_forced_counts=bool(include_forced_counts),
            )
            return (
                [batch_results for batch_results, _timing in handles],
                [dict(timing) for _batch_results, timing in handles],
            )

        prepared_results: list[list[FgResponseFrontierSolveResult]] = []
        timings: list[dict[str, float]] = []
        for batch in batches:
            prepared_results.append(
                GpuResponseKernelRunner.score_batch_sync(
                    batch,
                    include_forced_counts=bool(include_forced_counts),
                )
            )
            timings.append({})
        return prepared_results, timings
