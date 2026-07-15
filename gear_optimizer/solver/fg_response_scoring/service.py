from __future__ import annotations

from typing import Any

from gear_optimizer.solver.fg_response_scoring.planner import FgResponseFrontierPreparedPlan
from gear_optimizer.solver.fg_response_scoring.reducer import FgResultReducer


class FgResponseScoringService:
    """Materialize native FG owner results for a prepared exact Base surface."""

    @staticmethod
    def materialize_from_owner_score_map(
        plan: FgResponseFrontierPreparedPlan,
        owner_score_map: dict[tuple[int, ...], Any],
        *,
        include_forced_counts: bool = False,
    ) -> list[dict[str, Any]]:
        """Reduce a prepared plan against the fused owner-scored FG result map.

        The canonical production FG materialization for the exact Base-to-FG handoff.
        The GPU owner already scored FG straight from the typed Base surface's
        ``base_stats7`` and handed back ``owner_score_map``
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
            raise RuntimeError("FG fused materialization requires the Base owner FG score map")

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
                        f"{bc_key} (the owner did not score this Base candidate)"
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
