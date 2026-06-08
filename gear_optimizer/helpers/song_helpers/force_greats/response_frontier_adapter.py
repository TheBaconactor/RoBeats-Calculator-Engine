from __future__ import annotations

from typing import Any

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.helpers.song_helpers.force_greats.entry_utils import eval_data_from_entry, expected_selected_element
from gear_optimizer.helpers.song_helpers.ga_entry_utils import materialize_entry_names
from gear_optimizer.solver.fg_response_scoring.gpu_engine import GpuScoreEngine
from gear_optimizer.solver.fg_response_scoring.planner import (
    FgPlanner,
    FgResponseFrontierPreparedBatch,
    FgResponseFrontierPreparedPlan,
)
from gear_optimizer.solver.fg_response_scoring.reducer import (
    FgResultReducer,
    materialize_force_payload_from_response_frontier,
)
from gear_optimizer.solver.fg_response_scoring.service import FgResponseScoringService
from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
from gear_optimizer.solver.taichi_gem.force_greats import (
    FgResponseFrontierSolveResult,
    prepare_force_greats_response_frontier_scoring_batch,
    reconstruct_force_greats_response_trace,
)

__all__ = [
    "FgResponseFrontierPreparedBatch",
    "FgResponseFrontierPreparedPlan",
    "LOADOUTS_PER_SONG_LIMIT",
    "eval_data_from_entry",
    "expected_selected_element",
    "extract_fg_song_inputs",
    "materialize_entry_names",
    "prepare_force_greats_response_frontier_plan_for_ga_candidates",
    "prepare_force_greats_response_frontier_scoring_batch",
    "materialize_force_greats_response_frontier_plan_results",
    "reconstruct_force_greats_response_trace",
    "run_force_greats_response_frontier_for_ga_candidates",
    "score_force_greats_response_surface_exact",
    "_base_stats_for_response_frontier",
    "_force_payload_from_response_frontier",
    "_score_prepared_batches_for_plan",
]


def _base_stats_for_response_frontier(eval_data: dict[str, Any], *, selected: str) -> dict[str, Any]:
    return FgPlanner.base_stats_for_response_frontier(eval_data, selected=selected)


def _force_payload_from_response_frontier(**kwargs) -> dict[str, Any]:
    return materialize_force_payload_from_response_frontier(**kwargs)


def prepare_force_greats_response_frontier_plan_for_ga_candidates(
    ga_candidates,
    calc_song,
    ref_arrays,
    meta_primary_color,
    *,
    ga_registry=None,
    scoring_bundle=None,
) -> FgResponseFrontierPreparedPlan:
    return FgPlanner.plan_many(
        ga_candidates,
        calc_song,
        ref_arrays,
        meta_primary_color,
        ga_registry=ga_registry,
        scoring_bundle=scoring_bundle,
    )


def _score_prepared_batches_for_plan(
    plan: FgResponseFrontierPreparedPlan,
    *,
    gpu_client: Any | None,
) -> list[list[FgResponseFrontierSolveResult]]:
    return GpuScoreEngine.score_plan(
        plan,
        gpu_client=gpu_client,
        include_forced_counts=False,
    )[0]


def materialize_force_greats_response_frontier_plan_results(
    plan: FgResponseFrontierPreparedPlan,
    prepared_results: list[list[FgResponseFrontierSolveResult]],
) -> list[dict[str, Any]]:
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
