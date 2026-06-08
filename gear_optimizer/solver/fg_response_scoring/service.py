from __future__ import annotations

from typing import Any, Literal

from gear_optimizer.solver.fg_response_scoring.gpu_engine import GpuScoreEngine
from gear_optimizer.solver.fg_response_scoring.planner import FgPlanner, FgResponseFrontierPreparedPlan
from gear_optimizer.solver.fg_response_scoring.reducer import FgResultReducer

FgScoringMode = Literal["production", "sync", "skyline"]


class FgResponseScoringService:
    """One FG response-frontier entrypoint: plan → score → reduce."""

    @staticmethod
    def score_candidates(
        ga_candidates,
        calc_song,
        ref_arrays,
        meta_primary_color,
        *,
        ga_registry=None,
        scoring_bundle=None,
        gpu_client: Any | None = None,
        mode: FgScoringMode = "production",
    ) -> list[dict[str, Any]]:
        return FgResponseScoringService.score_candidates_with_stats(
            ga_candidates,
            calc_song,
            ref_arrays,
            meta_primary_color,
            ga_registry=ga_registry,
            scoring_bundle=scoring_bundle,
            gpu_client=gpu_client,
            mode=mode,
        )[0]

    @staticmethod
    def score_candidates_with_stats(
        candidates,
        calc_song,
        ref_arrays,
        meta_primary_color,
        *,
        ga_registry=None,
        scoring_bundle=None,
        gpu_client: Any | None = None,
        mode: FgScoringMode = "production",
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        if mode in ("sync", "skyline") and gpu_client is not None:
            raise ValueError(f"FgResponseScoringService mode={mode!r} requires gpu_client=None")
        if mode == "skyline":
            plan = FgPlanner.plan_skyline_candidate_records(
                candidates,
                calc_song,
                ref_arrays,
                meta_primary_color,
                scoring_bundle=scoring_bundle,
            )
        else:
            plan = FgPlanner.plan_many(
                candidates,
                calc_song,
                ref_arrays,
                meta_primary_color,
                ga_registry=ga_registry,
                scoring_bundle=scoring_bundle,
            )
        effective_client = None if mode in ("sync", "skyline") else gpu_client
        return (
            FgResponseScoringService.score_prepared_plan(
                plan,
                gpu_client=effective_client,
                mode=mode,
            ),
            FgResponseScoringService.plan_batch_stats(plan),
        )

    @staticmethod
    def plan_batch_stats(plan: FgResponseFrontierPreparedPlan) -> dict[str, int]:
        member_counts: dict[tuple[Any, ...], int] = {}
        for _entry, _eval_data, _selected, _base_stats, _paired_base_score, cache_key in plan.pending_jobs:
            member_counts[cache_key] = int(member_counts.get(cache_key, 0)) + 1
        unique_genomes = sum(len(prepared.rows) for prepared in plan.prepared_batches)
        input_genomes = len(plan.pending_jobs)
        return {
            "gpu_batches": int(unique_genomes),
            "groups": int(len(plan.prepared_batches)),
            "input_genomes": int(input_genomes),
            "unique_genomes": int(unique_genomes),
            "deduped_genomes": int(max(0, int(input_genomes) - int(unique_genomes))),
            "dedupe_groups": sum(1 for count in member_counts.values() if int(count) > 1),
        }

    @staticmethod
    def score_prepared_plan(
        plan: FgResponseFrontierPreparedPlan,
        *,
        gpu_client: Any | None,
        include_forced_counts: bool = False,
        mode: FgScoringMode = "production",
    ) -> list[dict[str, Any]]:
        prepared_results, _timings = GpuScoreEngine.score_plan(
            plan,
            gpu_client=gpu_client,
            include_forced_counts=bool(include_forced_counts),
        )
        return FgResultReducer.materialize(plan, prepared_results, skyline=mode == "skyline")

    @staticmethod
    def score_prepared_plan_with_timings(
        plan: FgResponseFrontierPreparedPlan,
        *,
        gpu_client: Any | None,
        include_forced_counts: bool = False,
    ) -> tuple[list[dict[str, Any]], list[dict[str, float]]]:
        prepared_results, timings = GpuScoreEngine.score_plan(
            plan,
            gpu_client=gpu_client,
            include_forced_counts=bool(include_forced_counts),
        )
        return FgResultReducer.materialize(plan, prepared_results), timings
