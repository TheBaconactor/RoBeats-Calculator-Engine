from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from gear_optimizer.solver.native_fg_owner import score_native_fg_candidate_surface
from gear_optimizer.solver.taichi_gem.force_greats import response_frontier


def _context():
    return SimpleNamespace(
        ref_arrays={"Perfect Points": np.ones(161)},
        cfg_data={"TotalBudget": 90},
        selected_color="Rush",
    )


def test_native_fg_scores_typed_base_stats_directly(monkeypatch):
    calls = []
    base_stats7 = np.arange(14, dtype=np.int64).reshape(2, 7)
    expected = {tuple(int(value) for value in row): object() for row in base_stats7}
    monkeypatch.setattr(
        response_frontier,
        "score_fused_owner_base_components_on_gpu_owner",
        lambda **kwargs: calls.append(kwargs) or expected,
    )
    result = score_native_fg_candidate_surface(
        base_stats7=base_stats7,
        context=_context(),
        scoring_bundle=object(),
        calc_song={"notes": []},
    )

    assert result is expected
    np.testing.assert_array_equal(calls[0]["base_components"], base_stats7)
    assert calls[0]["base_components"].dtype == np.int32
    assert calls[0]["selected_color"] == "Rush"
    assert calls[0]["total_budget"] == 90


def test_native_fg_rejects_empty_candidate_surface():
    with pytest.raises(ValueError, match="at least one Base candidate"):
        score_native_fg_candidate_surface(
            base_stats7=np.empty((0, 7), dtype=np.int32),
            context=_context(),
            scoring_bundle=object(),
            calc_song={},
        )
