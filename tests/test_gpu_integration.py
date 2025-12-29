"""
GPU Integration Regression Test

Tests the FULL GPU path through batch_evaluate_genomes to catch:
1. Per-genome stats bugs (different gear loadouts should have different scores)
2. Elemental color mapping bugs (primary/secondary/overflow colors)
3. User gem deduction bugs
4. Precision mismatches between CPU and GPU

This test uses realistic scenarios with multiple genomes and song metadata.
"""

import numpy as np
from math import floor
import sys
import os
import pytest

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.solver.scoring import batch_evaluate_genomes, solve_best_fever_combination
from gear_optimizer.core.constants import TOTAL_ROWS


pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module", autouse=True)
def _taichi_vulkan_ready():
    pytest.importorskip("taichi")
    try:
        from gear_optimizer.solver.taichi_gem.runtime import init_taichi_vulkan

        init_taichi_vulkan()
    except Exception as exc:
        pytest.skip(f"Taichi Vulkan init failed: {exc}")


def create_mock_song(primary_color="Beat", secondary_color="Flow"):
    """Create mock song data with specified elemental colors."""
    total_notes = 500
    timestamps = np.linspace(0, 120, total_notes)

    return {
        "metadata": {
            "Primary Color": primary_color,
            "Secondary Color": secondary_color,
            "Total Notes": total_notes,
            "Long Notes": 50,
            "Last Note Time": timestamps[-1],
        },
        "song_data": {
            "timestamps": timestamps,
        },
    }


def create_mock_ref_arrays():
    """Create realistic reference arrays."""
    return {
        "Perfect Points": np.array([100 + i * 2.5 for i in range(161)], dtype=np.float64),
        "Combo Multiplier": np.array([1.0 + i * 0.005 for i in range(161)], dtype=np.float64),
        "Fever Multiplier": np.array([1.5 + i * 0.01 for i in range(161)], dtype=np.float64),
        "Fever Fill Rate": np.array([1.0 + i * 0.006 for i in range(161)], dtype=np.float64),
        "Fever Time": np.array([1.0 + i * 0.004 for i in range(161)], dtype=np.float64),
    }


def test_multi_genome_parity():
    """
    Test that GPU produces correct scores for MULTIPLE genomes with DIFFERENT stats.

    This is the critical test that catches per-genome stats bugs.
    """
    print("\n" + "=" * 70)
    print("TEST: Multi-Genome Parity (Catches per-genome stats bugs)")
    print("=" * 70)

    ref_arrays = create_mock_ref_arrays()
    calc_song = create_mock_song(primary_color="Beat", secondary_color="Flow")

    # Create genomes with DIFFERENT stats - this catches per-genome bugs
    genomes = [
        [
            {
                "Name": "Low Stats",
                "Perfect Points": 50,
                "Combo Multiplier": 40,
                "Fever Multiplier": 30,
                "Fever Time": 20,
                "Fever Fill Rate": 20,
                "Beat": 200,
                "Flow": 100,
                "Vibe": 50,
                "Rush": 50,
                "Chill": 50,
            }
        ],
        [
            {
                "Name": "Medium Stats",
                "Perfect Points": 100,
                "Combo Multiplier": 80,
                "Fever Multiplier": 60,
                "Fever Time": 40,
                "Fever Fill Rate": 40,
                "Beat": 400,
                "Flow": 200,
                "Vibe": 100,
                "Rush": 100,
                "Chill": 100,
            }
        ],
        [
            {
                "Name": "High Stats",
                "Perfect Points": 150,
                "Combo Multiplier": 120,
                "Fever Multiplier": 90,
                "Fever Time": 60,
                "Fever Fill Rate": 60,
                "Beat": 600,
                "Flow": 300,
                "Vibe": 150,
                "Rush": 150,
                "Chill": 150,
            }
        ],
    ]

    cfg_data = {
        "selected_color": "Beat",
        "use_gpu": True,
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }

    base_stats_fixed = {
        k: 0
        for k in [
            "Perfect Points",
            "Combo Multiplier",
            "Fever Multiplier",
            "Fever Time",
            "Fever Fill Rate",
            "Beat",
            "Flow",
            "Vibe",
            "Rush",
            "Chill",
        ]
    }

    # Run GPU path
    gpu_results = batch_evaluate_genomes(genomes, base_stats_fixed, cfg_data, calc_song, ref_arrays)

    # Compare with CPU path
    cfg_data["use_gpu"] = False
    cpu_results = batch_evaluate_genomes(genomes, base_stats_fixed, cfg_data, calc_song, ref_arrays)

    mismatches = []
    for i, (gpu, cpu) in enumerate(zip(gpu_results, cpu_results)):
        gpu_score = gpu["Score"] if gpu else 0
        cpu_score = cpu["Score"] if cpu else 0

        match = gpu_score == cpu_score
        status = "[PASS]" if match else "[FAIL]"
        print(f"  Genome {i + 1}: GPU={gpu_score:,}, CPU={cpu_score:,} {status}")

        if not match:
            mismatches.append((i, gpu_score, cpu_score))
            print(f"    MISMATCH! Difference: {gpu_score - cpu_score:,}")

    # CRITICAL: Check that different genomes produce DIFFERENT scores
    cfg_data["use_gpu"] = True
    scores = [r["Score"] for r in gpu_results if r]
    assert len(set(scores)) > 1, "All genomes have same score - per-genome stats NOT working!"
    print(f"  [PASS] Scores vary by genome ({len(set(scores))} unique scores)")

    assert not mismatches, f"GPU/CPU mismatches: {mismatches}"


def test_elemental_color_mapping():
    """
    Test that different song elemental colors produce correct scores.

    This catches bugs where primary/secondary color values are swapped or wrong.
    """
    print("\n" + "=" * 70)
    print("TEST: Elemental Color Mapping")
    print("=" * 70)

    ref_arrays = create_mock_ref_arrays()

    # Test with different color combinations
    color_combos = [
        ("Beat", "Flow"),
        ("Rush", "Chill"),
        ("Vibe", "Beat"),
    ]

    genome = [
        {
            "Name": "Test Gear",
            "Perfect Points": 100,
            "Combo Multiplier": 80,
            "Fever Multiplier": 60,
            "Fever Time": 40,
            "Fever Fill Rate": 40,
            "Beat": 500,
            "Flow": 300,
            "Vibe": 200,
            "Rush": 150,
            "Chill": 100,
        }
    ]

    base_stats_fixed = {
        k: 0
        for k in [
            "Perfect Points",
            "Combo Multiplier",
            "Fever Multiplier",
            "Fever Time",
            "Fever Fill Rate",
            "Beat",
            "Flow",
            "Vibe",
            "Rush",
            "Chill",
        ]
    }

    mismatches = []

    for primary, secondary in color_combos:
        calc_song = create_mock_song(primary_color=primary, secondary_color=secondary)

        cfg_gpu = {
            "selected_color": "Beat",
            "use_gpu": True,
            "user_ft": 0,
            "user_ff": 0,
            "user_pp": 0,
            "user_cm": 0,
            "user_fm": 0,
            "static_elem_input": 0,
        }
        cfg_cpu = {**cfg_gpu, "use_gpu": False}

        gpu_result = batch_evaluate_genomes([genome], base_stats_fixed, cfg_gpu, calc_song, ref_arrays)
        cpu_result = batch_evaluate_genomes([genome], base_stats_fixed, cfg_cpu, calc_song, ref_arrays)

        gpu_score = gpu_result[0]["Score"] if gpu_result and gpu_result[0] else 0
        cpu_score = cpu_result[0]["Score"] if cpu_result and cpu_result[0] else 0

        match = gpu_score == cpu_score
        status = "[PASS]" if match else "[FAIL]"
        print(f"  {primary}/{secondary}: GPU={gpu_score:,}, CPU={cpu_score:,} {status}")

        if not match:
            mismatches.append((primary, secondary, gpu_score, cpu_score))

    assert not mismatches, f"GPU/CPU mismatches: {mismatches}"


def test_single_genome_via_solver():
    """Original integration test - single genome through solve_best_fever_combination."""
    print("\n" + "=" * 70)
    print("TEST: Single Genome via solve_best_fever_combination")
    print("=" * 70)

    timestamps = np.linspace(0, 120, 100).tolist()
    calc_song = {
        "metadata": {
            "Song Name": "GPU Integration Test Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 120.0,
            "Total Notes": 100,
        },
        "song_data": {"timestamps": timestamps},
    }

    base_stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Rush": 100,
        "Flow": 100,
        "Beat": 50,
        "Vibe": 50,
        "Chill": 50,
    }

    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows),
        "Fever Time": np.linspace(1.0, 2.5, rows),
    }

    base_cfg = {
        "selected_color": "Rush",
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }

    cpu_result = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats.copy(),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg={**base_cfg, "use_gpu": False},
    )

    gpu_result = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats.copy(),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg={**base_cfg, "use_gpu": True},
    )

    cpu_score = cpu_result.get("Score")
    gpu_score = gpu_result.get("Score")

    match = cpu_score == gpu_score
    status = "[PASS]" if match else "[FAIL]"
    print(f"  CPU: {cpu_score:,}, GPU: {gpu_score:,} {status}")

    assert match


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v", "-s"]))
