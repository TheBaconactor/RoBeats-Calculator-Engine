"""ForceGreats response-frontier public entrypoints (delegate to fg_response_scoring)."""

from __future__ import annotations

from typing import Any

__all__ = [
    "FgResponseFrontierPreparedBatch",
    "FgResponseFrontierPreparedPlan",
    "materialize_force_greats_response_frontier_plan_results",
    "prepare_force_greats_response_frontier_plan_for_ga_candidates",
    "run_force_greats_response_frontier_for_ga_candidates",
]


def prepare_force_greats_response_frontier_plan_for_ga_candidates(
    ga_candidates,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    ga_registry=None,
    scoring_bundle=None,
):
    from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner

    return FgPlanner.plan_many(
        ga_candidates,
        calc_song,
        ref_arrays,
        meta_primary_color,
        ga_registry=ga_registry,
        scoring_bundle=scoring_bundle,
    )


def materialize_force_greats_response_frontier_plan_results(plan, prepared_results):
    from gear_optimizer.solver.fg_response_scoring.reducer import FgResultReducer

    return FgResultReducer.materialize(plan, prepared_results)


def run_force_greats_response_frontier_for_ga_candidates(
    ga_candidates,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    ga_registry=None,
    scoring_bundle=None,
    gpu_client: Any | None = None,
) -> list[dict[str, Any]]:
    from gear_optimizer.solver.fg_response_scoring.service import FgResponseScoringService

    mode = "sync" if gpu_client is None else "production"
    return FgResponseScoringService.score_candidates(
        ga_candidates,
        calc_song,
        ref_arrays,
        meta_primary_color,
        ga_registry=ga_registry,
        scoring_bundle=scoring_bundle,
        gpu_client=gpu_client,
        mode=mode,
    )


def __getattr__(name: str):
    if name == "FgResponseFrontierPreparedBatch":
        from gear_optimizer.solver.fg_response_scoring.planner import FgResponseFrontierPreparedBatch

        return FgResponseFrontierPreparedBatch
    if name == "FgResponseFrontierPreparedPlan":
        from gear_optimizer.solver.fg_response_scoring.planner import FgResponseFrontierPreparedPlan

        return FgResponseFrontierPreparedPlan
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
