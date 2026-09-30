from __future__ import annotations

from typing import Any

from gear_optimizer.pipeline.results import SolvedFg, SolvedLoadout
from gear_optimizer.solver.fg_response_scoring.gpu_engine import GpuScoreEngine
from gear_optimizer.solver.fg_response_scoring.planner import FgResponseFrontierPreparedPlan
from gear_optimizer.solver.fg_response_scoring.reducer import FgResultReducer


class FgResponseScoringService:
    """FG scoring of a prepared plan, reduced to typed results (the reducer's contract)."""

    @staticmethod
    def materialize_from_owner_score_map(
        plan: FgResponseFrontierPreparedPlan,
        owner_score_map: dict[tuple[int, ...], Any],
    ) -> list[tuple[SolvedLoadout, SolvedFg]]:
        """Reduce a prepared plan against the fused owner-scored FG result map.

        The canonical production FG materialization for the fused GA->FG handoff
        (Slice 3). The GPU owner already scored FG straight from the device
        base_stats7 in the GA turn and handed back ``owner_score_map``
        ({base_components_7tuple -> FgFusedOwnerScoreRow}). Here, off the owner's
        critical path, each prepared batch row's solve result is rebuilt from the map
        (keyed by the batch's ``base_components``, which the owner scored over the
        identical payload), then the shared reducer applies paired-base authority +
        the exact surface rescore. No GPU work.
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
            # Song-invariant hoists shared across the batch's candidates (mirrors the batch
            # materialize sibling in response_frontier.py): song_inputs is a pure function of
            # batch.song and each frontier is a pure function of its (ft_stat, ff_stat)
            # over the same song/ref/scoring bundle, so only the stat-key suffix varies per
            # candidate. Rebuilding the full song fingerprint + extract per candidate was pure
            # waste on the shared LRU; carry them once per batch instead.
            song_inputs = batch.song.fg_inputs
            frontier_by_stat_key: dict[tuple[int, int], Any] = {}
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
                        song=batch.song,
                        curves=batch.curves,
                        scoring_bundle=batch.scoring_bundle,
                        started=batch.started,
                        include_forced_counts=False,
                        song_inputs=song_inputs,
                        frontier_by_stat_key=frontier_by_stat_key,
                    )
                )
            prepared_results.append(batch_results)
        return FgResultReducer.materialize(plan, prepared_results)

    @staticmethod
    def score_plan(plan: FgResponseFrontierPreparedPlan) -> list[tuple[SolvedLoadout, SolvedFg]]:
        """The pre-fusion reference route: the plan's batches scored synchronously on the GPU owner, then reduced
        like the fused route (the parity tests compare the two)."""
        return FgResultReducer.materialize(plan, GpuScoreEngine.score_plan(plan))
