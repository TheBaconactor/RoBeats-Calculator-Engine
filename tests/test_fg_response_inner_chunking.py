from __future__ import annotations

from tests.curves_support import synthetic_curves
import numpy as np
import pytest


def test_response_surface_head_coeffs_match_bruteforce():
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_patterns import surface_head_coeffs

    surface_words = np.asarray(
        [
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0, 0, 0],
            [0b10101, 0x80000001, 0x0000FFFF, 0x0000000F, 0, 0, 0, 0],
            [0xAAAAAAAA, 0x55555555, 0x33333333, 0xCCCCCCCC, 0, 0, 0, 0],
        ],
        dtype=np.uint32,
    )

    for head_len in (0, 1, 31, 32, 33, 63, 64, 65, 96, 100, 120):
        expected = np.zeros((int(surface_words.shape[0]), 4), dtype=np.int32)
        head = max(0, min(int(head_len), 100))
        for row_idx, row in enumerate(surface_words):
            for pos0 in range(head):
                block = int(pos0 // 32)
                bit = int(pos0 % 32)
                is_fever = (int(row[block]) >> bit) & 1
                expected[row_idx, 1 if is_fever else 0] += 1
                expected[row_idx, 3 if is_fever else 2] += int(pos0 + 1)

        got = surface_head_coeffs(surface_words, head_len=int(head_len))
        np.testing.assert_array_equal(got, expected)


def test_cpu_scorer_shared_pattern_ids_preserve_complete_winner_row() -> None:
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_patterns import surface_head_coeffs
    from gear_optimizer.solver.taichi_gem.force_greats.response_gem_search import _score_response_group_meta_cpu

    pattern_a = np.zeros((8,), dtype=np.uint32)
    pattern_b = np.zeros((8,), dtype=np.uint32)
    pattern_b[0] = np.uint32(0b0101)
    identity_words = np.stack((pattern_a, pattern_a, pattern_b)).astype(np.uint32)
    shared_words = np.stack((pattern_a, pattern_b)).astype(np.uint32)
    counts = np.asarray(((0, 0, 0), (2, 0, 0), (1, 0, 0)), dtype=np.int32)
    group_meta = np.asarray(((0, 10, 10, 10, 120, 60, 4, 3),), dtype=np.int32)
    common = {
        "group_meta": group_meta,
        "group_offsets": np.asarray((0,), dtype=np.int32),
        "group_lengths": np.asarray((3,), dtype=np.int32),
        "candidate_slices": ((0, 1),),
        "primary_color": "Rush",
        "secondary_color": "Flow",
        "selected_color": "Rush",
        "curves": synthetic_curves({
            "Perfect Points": np.linspace(1.0, 2.0, MAX_STAT + 1, dtype=np.float64),
            "Combo Multiplier": np.linspace(2.0, 2.6, MAX_STAT + 1, dtype=np.float64),
            "Fever Multiplier": np.linspace(3.0, 5.0, MAX_STAT + 1, dtype=np.float64),
        }),
        "surface_counts": counts,
    }
    identity = _score_response_group_meta_cpu(
        **common,
        surface_pattern_ids=np.asarray((0, 1, 2), dtype=np.int32),
        surface_pattern_words=identity_words,
        surface_pattern_head_coeffs=surface_head_coeffs(identity_words, head_len=4),
    )
    shared = _score_response_group_meta_cpu(
        **common,
        surface_pattern_ids=np.asarray((0, 0, 1), dtype=np.int32),
        surface_pattern_words=shared_words,
        surface_pattern_head_coeffs=surface_head_coeffs(shared_words, head_len=4),
    )

    np.testing.assert_array_equal(shared, identity)


