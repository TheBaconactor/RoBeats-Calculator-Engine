from __future__ import annotations

import pytest

from tools.bench.bench_ga_winner_stability import _extract_top_hashes, summarize_depth_runs


def test_extract_top_hashes_uses_best_base_and_fg_entries():
    base_hash, fg_hash = _extract_top_hashes(
        [
            {"loadout_hash": "hash_a", "score": 100, "fg_score": 110},
            {"loadout_hash": "hash_b", "score": 120, "fg_score": 105},
            {"loadout_hash": "hash_c", "score": 90, "fg_score": 140},
        ]
    )

    assert base_hash == "hash_b"
    assert fg_hash == "hash_c"


def test_extract_top_hashes_falls_back_to_computed_hash():
    base_hash, fg_hash = _extract_top_hashes(
        [
            {
                "score": 120,
                "fg_score": 90,
                "gear": ["gear_a", "gear_b"],
                "minis": ["mini_a", "mini_b", "mini_c"],
            }
        ]
    )

    assert isinstance(base_hash, str) and len(base_hash) == 32
    assert fg_hash == base_hash


def test_summarize_depth_runs_reports_stability_and_timing_means():
    summary = summarize_depth_runs(
        [
            {
                "best_score": 100,
                "best_fg_score": 120,
                "base_hash": "hash_a",
                "fg_hash": "fg_a",
                "duplicate_genome_ratio": 0.10,
                "elapsed_wall_sec": 5.0,
                "stage_timing": {"cpu_ga_wall_sec": 3.0, "cpu_fg_wall_sec": 1.0},
                "gpu_timing": {"kernel_sec": 2.0},
            },
            {
                "best_score": 110,
                "best_fg_score": 125,
                "base_hash": "hash_a",
                "fg_hash": "fg_b",
                "duplicate_genome_ratio": 0.20,
                "elapsed_wall_sec": 7.0,
                "stage_timing": {"cpu_ga_wall_sec": 4.0, "cpu_fg_wall_sec": 1.5},
                "gpu_timing": {"kernel_sec": 3.0},
            },
            {
                "best_score": 90,
                "best_fg_score": 119,
                "base_hash": "hash_b",
                "fg_hash": "fg_b",
                "duplicate_genome_ratio": 0.30,
                "elapsed_wall_sec": 6.0,
                "stage_timing": {"cpu_ga_wall_sec": 5.0, "cpu_fg_wall_sec": 2.0},
                "gpu_timing": {"kernel_sec": 4.0},
            },
        ]
    )

    assert summary["runs"] == 3
    assert summary["unique_base_hashes"] == 2
    assert summary["base_mode_hash"] == "hash_a"
    assert summary["base_mode_count"] == 2
    assert summary["base_stability_ratio"] == pytest.approx(2 / 3)
    assert summary["duplicate_genome_ratio"]["mean"] == pytest.approx(0.20)
    assert summary["elapsed_wall_sec"]["mean"] == pytest.approx(6.0)
    assert summary["stage_timing"]["cpu_ga_wall_sec"]["mean"] == pytest.approx(4.0)
    assert summary["gpu_timing"]["kernel_sec"]["mean"] == pytest.approx(3.0)
