from __future__ import annotations

from pathlib import Path


def _dominates(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    return all(x >= y for x, y in zip(a, b, strict=True)) and any(x > y for x, y in zip(a, b, strict=True))


def _s7_select(
    current_score: int, current_stats: tuple[int, ...], candidate_score: int, candidate_stats: tuple[int, ...]
) -> bool:
    """Mirror the production-safe S7 rule: score first, dominance only on exact ties."""
    return candidate_score > current_score or (
        candidate_score == current_score and _dominates(candidate_stats, current_stats)
    )


def test_s7_exact_tie_updates_only_for_pointwise_dominance() -> None:
    current = (10, 10, 10, 10, 10, 10, 10)
    dominates_current = (11, 10, 10, 10, 10, 10, 10)
    lexicographic_only = (11, 1, 1, 1, 1, 1, 1)

    assert _s7_select(1000, current, 1000, dominates_current)
    assert not _s7_select(1000, current, 1000, lexicographic_only)
    assert not _s7_select(1000, current, 999, dominates_current)
    assert _s7_select(1000, current, 1001, lexicographic_only)


def test_s8_score_bucket_key_is_not_lossless_for_exact_score_objective() -> None:
    epsilon = 100
    higher_score_weaker_stats = (1000 // (epsilon + 1), (0, 0, 0, 0, 0, 0, 0))
    lower_score_stronger_stats = (999 // (epsilon + 1), (99, 99, 99, 99, 99, 99, 99))

    assert lower_score_stronger_stats > higher_score_weaker_stats
    assert 999 < 1000


def test_kernel_uses_exact_score_tie_dominance_without_near_tie_bucket() -> None:
    src = Path("gear_optimizer/solver/taichi_gem/kernels/kernels_ga.py").read_text(encoding="utf-8")

    assert "def _base_stats_dominates" in src
    assert "sc == best_a_score and _base_stats_dominates(idx, best_a) != 0" in src
    assert "sc == best_b_score" in src
    assert "score //" not in src
    assert "N_body" not in src
