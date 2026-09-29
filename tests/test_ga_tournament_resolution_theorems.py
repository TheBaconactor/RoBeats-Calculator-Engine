from __future__ import annotations

from pathlib import Path


def test_kernel_uses_exact_score_tie_dominance_without_near_tie_bucket() -> None:
    src = Path("gear_optimizer/solver/taichi_gem/kernels/kernels_ga.py").read_text(encoding="utf-8")

    assert "def _base_stats_dominates" in src
    assert "sc == best_a_score and _base_stats_dominates(idx, best_a) != 0" in src
    assert "sc == best_b_score" in src
    assert "score //" not in src
    assert "N_body" not in src
