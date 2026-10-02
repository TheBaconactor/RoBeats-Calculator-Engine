from __future__ import annotations

from gear_optimizer.solver.fg_response_scoring.planner import FgResponseFrontierPreparedPlan
from gear_optimizer.solver.taichi_gem.force_greats import FgResponseFrontierSolveResult
from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
    score_prepared_force_greats_response_frontier_batch_sync,
)


class GpuScoreEngine:
    """Score prepared FG response-frontier batches synchronously on the GPU owner.

    The pre-fusion reference route (FgResponseScoringService.score_plan). Production FG does not go through here:
    the GPU owner scores FG in the GA turn and the FG worker reduces the owner's score map
    (FgResponseScoringService.materialize_from_owner_score_map).
    """

    @staticmethod
    def score_plan(plan: FgResponseFrontierPreparedPlan) -> list[list[FgResponseFrontierSolveResult]]:
        return [
            score_prepared_force_greats_response_frontier_batch_sync(prepared.batch)
            for prepared in plan.prepared_batches
        ]
