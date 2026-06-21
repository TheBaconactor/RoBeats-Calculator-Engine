from __future__ import annotations

from typing import Any, Literal

from gear_optimizer.solver.fg_response_scoring.gpu_engine import GpuScoreEngine
from gear_optimizer.solver.fg_response_scoring.planner import (
    FgPlanner,
    FgResponseFrontierPreparedPlan,
)
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
    def materialize_from_owner_score_map(
        plan: FgResponseFrontierPreparedPlan,
        owner_score_map: dict[tuple[int, ...], Any],
        *,
        include_forced_counts: bool = False,
    ) -> list[dict[str, Any]]:
        """Reduce a prepared plan against the fused owner-scored FG result map.

        The canonical production FG materialization for the fused GA->FG handoff
        (Slice 3). The GPU owner already scored FG straight from the device
        base_stats7 in the GA turn and handed back ``owner_score_map``
        ({base_components_7tuple -> FgFusedOwnerScoreRow}). Here, off the owner's
        critical path, each prepared batch row's solve result is rebuilt from the map
        (keyed by the batch's ``base_components``, which the owner scored over the
        identical payload), then the shared reducer applies paired-base authority +
        the winner gate + exact surface rescore. No GPU work.
        """
        from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
            build_fused_owner_solve_result_from_score_row,
        )

        if owner_score_map is None:
            raise RuntimeError("FG fused materialization requires the owner FG score map from the GA turn")

        prepared_results = []
        for prepared in plan.prepared_batches:
            batch = prepared.batch
            base_components = batch.base_components
            rows = list(prepared.rows)
            if int(base_components.shape[0]) != len(rows):
                raise RuntimeError("FG fused materialization: prepared batch base_components/rows length mismatch")
            batch_results = []
            for row_idx, (_cache_key, base_stats) in enumerate(rows):
                bc_key = tuple(int(v) for v in base_components[int(row_idx)].tolist())
                score_row = owner_score_map.get(bc_key)
                if score_row is None:
                    raise RuntimeError(
                        "FG fused materialization: owner score map missing base_components "
                        f"{bc_key} (the owner did not score this candidate in the GA turn)"
                    )
                batch_results.append(
                    build_fused_owner_solve_result_from_score_row(
                        score_row=score_row,
                        base_stats=base_stats,
                        selected_color=batch.selected_color,
                        calc_song=batch.calc_song,
                        ref_arrays=batch.ref_arrays,
                        scoring_bundle=batch.scoring_bundle,
                        started=batch.started,
                        include_forced_counts=bool(include_forced_counts),
                    )
                )
            prepared_results.append(batch_results)
        return FgResultReducer.materialize(plan, prepared_results)

    @staticmethod
    def score_prepared_plan(
        plan: FgResponseFrontierPreparedPlan,
        *,
        gpu_client: Any | None,
        include_forced_counts: bool = False,
        mode: FgScoringMode = "production",
    ) -> list[dict[str, Any]]:
        # Synchronous owner-thread FG scoring path: skyline (the test-only GA
        # alternative) and the non-native helper route here with gpu_client=None. The
        # production native in-flight FG path is the FUSED owner continuation (the GPU
        # owner scores FG in the GA turn; materialize_from_owner_score_map reduces it),
        # which never submits a separate FG batch request -- so an FG GPU client is no
        # longer a scoring route. A passed gpu_client is therefore an invalid call.
        if gpu_client is not None:
            raise ValueError(
                "FgResponseScoringService.score_prepared_plan no longer scores via a GPU "
                "client; the production native FG path uses the fused owner continuation "
                "(materialize_from_owner_score_map). Pass gpu_client=None."
            )
        prepared_results, _timings = GpuScoreEngine.score_plan(
            plan,
            gpu_client=None,
            include_forced_counts=bool(include_forced_counts),
        )
        return FgResultReducer.materialize(plan, prepared_results, skyline=mode == "skyline")
