from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from gear_optimizer.solver.exact_base_candidate_surface import ExactBaseCandidateSurface
from gear_optimizer.solver.exact_base_pipeline_decode import decode_exact_base_pipeline_result
from gear_optimizer.solver.exact_base_search import (
    ExactBasePipelineResult,
    ExactBaseScoredPool,
    ExactBaseSearchTelemetry,
)
from gear_optimizer.solver.force_greats_common import FG_BASE_STATS7_KEY
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats


class _Registry:
    def decode_loadout(self, ids):
        return [{"Name": f"item-{int(item_id)}", "Perfect Points": 1} for item_id in ids]


def test_decode_exact_base_pipeline_result_preserves_ranked_surface_without_duplicate_winner():
    ids = np.asarray(
        [
            [1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 2, 3, 4, 5, 6, 7, 8, 10],
        ],
        dtype=np.int32,
    )
    scores = np.asarray([500, 490], dtype=np.int32)
    results = np.asarray([[500, 1, 2, 3, 4, 5, 6], [490, 2, 1, 4, 3, 2, 1]], dtype=np.int32)
    base_stats7 = np.asarray([[20, 30, 40, 50, 60, 70, 80], [21, 31, 41, 51, 61, 71, 81]], dtype=np.int32)
    surface = ExactBaseCandidateSurface(
        candidate_ids=ids,
        base_scores=scores,
        result_rows=results,
        base_stats7=base_stats7,
    )
    pool = ExactBaseScoredPool(
        candidate_ids=ids,
        scores=scores,
        best_ids=ids[0],
        best_score=500,
        telemetry=ExactBaseSearchTelemetry(phase_seconds={}, counts={}),
    )
    result = ExactBasePipelineResult(scored_pool=pool, candidate_surface=surface)
    context = SimpleNamespace(
        registry=_Registry(),
        gpu_arrays={"item_stats": np.zeros((11, 10), dtype=np.int32)},
        base_fixed_stats_arr=np.zeros(10, dtype=np.int32),
        selected_color="Rush",
    )

    best_data, best_gear, best_minis, candidates = decode_exact_base_pipeline_result(
        result=result,
        context=context,
    )

    assert best_data["Score"] == 500
    assert len(best_gear) == 6
    assert len(best_minis) == 3
    assert [candidate["BaseScore"] for candidate in candidates] == [500, 490]
    assert len(candidates) == 2
    assert candidates[0]["LoadoutIDs"] == ids[0].tolist()
    assert best_data["LoadoutIDs"] == ids[0].tolist()
    assert len(best_data["Loadout"]) == 9
    assert candidates[0]["Data"][FG_BASE_STATS7_KEY] == tuple(base_stats7[0].tolist())
    candidate_data = candidates[0]["Data"]
    assert candidate_data["Stats"] == apply_gems_to_base_stats(
        candidate_data["BaseStats"],
        "Rush",
        1,
        2,
        3,
        4,
        5,
        6,
    )
    assert candidate_data["Stats"] != candidate_data["BaseStats"]
