from __future__ import annotations

import numpy as np

from gear_optimizer.helpers.song_helpers.force_greats.ftff_pairs import reduce_ftff_pairs_by_surface_keys


def test_cell_stability_margin_must_exceed_two_delta_not_delta() -> None:
    """BASE-5/FG-7 need M > 2Δ for reuse; M > Δ alone can reverse the winner."""
    center_best = 10.0
    center_alt = 0.0
    margin = center_best - center_alt
    delta = 6.0

    moved_best = center_best - delta
    moved_alt = center_alt + delta

    assert margin > delta
    assert moved_alt > moved_best
    assert margin < 2 * delta


def test_cell_stability_is_safe_when_margin_exceeds_two_delta() -> None:
    center_best = 20.0
    center_alt = 0.0
    margin = center_best - center_alt
    delta = 9.0

    worst_best = center_best - delta
    worst_alt = center_alt + delta

    assert margin > 2 * delta
    assert worst_best > worst_alt


def test_admissible_bound_exclusion_requires_strictly_below_incumbent() -> None:
    exact_scores = [91, 95, 97]
    admissible_upper_bound = 99
    incumbent = 100

    assert admissible_upper_bound >= max(exact_scores)
    assert admissible_upper_bound < incumbent
    assert all(score < incumbent for score in exact_scores)

    tied_incumbent = 99
    assert admissible_upper_bound == tied_incumbent
    assert not admissible_upper_bound < tied_incumbent


def test_bound_exclusion_is_false_without_admissibility() -> None:
    claimed_upper_bound = 99
    incumbent = 100
    actual_candidate_score = 105

    assert claimed_upper_bound < incumbent
    assert actual_candidate_score > incumbent
    assert claimed_upper_bound < actual_candidate_score


def test_irrelevant_section_requires_same_surface_and_lower_penalty() -> None:
    same_surface_base_score = 1000
    zero_count_penalty = 0
    positive_count_penalty = 12

    assert same_surface_base_score - zero_count_penalty > same_surface_base_score - positive_count_penalty

    changed_surface_base_score = 1040
    assert changed_surface_base_score - positive_count_penalty > same_surface_base_score - zero_count_penalty


def test_ftff_boundary_representative_must_be_full_pareto_frontier() -> None:
    """A cheapest-only representative can miss an elemental tradeoff inside one exact surface."""
    pairs = np.asarray([(0, 0), (1, 0)], dtype=np.int32)

    result = reduce_ftff_pairs_by_surface_keys(
        pairs,
        ["same-exact-surface", "same-exact-surface"],
        total_budget=10,
        is_p_ft=1,
    )

    assert result.dropped == 0
    assert result.pairs.tolist() == [[0, 0], [1, 0]]


def test_unified_key_cannot_use_current_multiplier_without_future_trajectory() -> None:
    """Moonshot-5: current table bucket equality is not enough for exact equivalence."""
    ref_pp = np.ones((20,), dtype=np.int32) * 100
    ref_pp[12] = 101
    ref_pp[13] = 200

    pp_a = 10
    pp_b = 11
    gem_step = 2

    assert ref_pp[pp_a] == ref_pp[pp_b]
    assert ref_pp[pp_a + gem_step] != ref_pp[pp_b + gem_step]


def test_large_antichain_refutes_small_universal_upper_envelope_assumption() -> None:
    """Moonshot-7's envelope exists, but finite monotone domains can have large skylines."""
    width = 12
    dims = 4
    points = []
    for a in range(width + 1):
        for b in range(width + 1):
            for c in range(width + 1):
                d = width - a - b - c
                if d >= 0:
                    points.append((a, b, c, d))

    for i, p in enumerate(points):
        for q in points[i + 1 :]:
            p_dominates_q = all(x >= y for x, y in zip(p, q, strict=True)) and any(
                x > y for x, y in zip(p, q, strict=True)
            )
            q_dominates_p = all(x >= y for x, y in zip(q, p, strict=True)) and any(
                x > y for x, y in zip(q, p, strict=True)
            )
            assert not p_dominates_q
            assert not q_dominates_p

    assert len(points) == 455
