from __future__ import annotations

from typing import Any

from gear_optimizer.solver.fg_response_scoring.planner import FgResponseFrontierPreparedPlan
from gear_optimizer.solver.taichi_gem.force_greats import FgResponseFrontierSolveResult
from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
    score_prepared_force_greats_response_frontier_batch_sync,
)


class GpuScoreEngine:
    """Score prepared FG response-frontier batches synchronously on the GPU owner.

    This is the owner-thread SYNC path used by skyline (the test-only GA alternative)
    and the non-native helper. The production native in-flight FG path does NOT go
    through here: it is the fused owner continuation (the GPU owner scores FG in the GA
    turn and the driver reduces via FgResponseScoringService.materialize_from_owner
    _score_map). ``gpu_client`` must be None.
    """

    @staticmethod
    def score_plan(
        plan: FgResponseFrontierPreparedPlan,
        *,
        gpu_client: Any | None,
        include_forced_counts: bool = False,
    ) -> tuple[list[list[FgResponseFrontierSolveResult]], list[dict[str, float]]]:
        # `timings` is a per-batch shape the callers unpack-and-discard (`_timings`).
        # The via-client branch that populated it was deleted with the fused handoff;
        # the empty-dict list is retained as the stable return shape.
        if gpu_client is not None:
            raise ValueError(
                "GpuScoreEngine.score_plan is the synchronous owner-thread path "
                "(gpu_client=None); the production native FG path uses the fused owner "
                "continuation. Pass gpu_client=None."
            )
        batches = [prepared.batch for prepared in plan.prepared_batches]
        prepared_results: list[list[FgResponseFrontierSolveResult]] = []
        timings: list[dict[str, float]] = []
        for batch in batches:
            prepared_results.append(
                score_prepared_force_greats_response_frontier_batch_sync(
                    batch,
                    include_forced_counts=bool(include_forced_counts),
                )
            )
            timings.append({})
        return prepared_results, timings
