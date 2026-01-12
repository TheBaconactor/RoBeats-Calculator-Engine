"""
GPU timeline parity test.

Verifies that the GPU-computed 161×161 fever timeline grid matches the CPU reference
for the fields that downstream kernels depend on (gap + fever activations).
"""

import os
import sys

import numpy as np
import pytest

# Add repo root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module", autouse=True)
def _taichi_vulkan_ready():
    pytest.importorskip("taichi")
    try:
        from gear_optimizer.solver.taichi_gem.runtime import init_taichi_vulkan

        init_taichi_vulkan()
    except Exception as exc:
        pytest.skip(f"Taichi Vulkan init failed: {exc}")


def _create_mock_ref_arrays():
    rows = 161
    # Taichi runtime expects these core lookup tables to be present.
    return {
        "Perfect Points": np.linspace(100.0, 200.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }


def _create_mock_song(*, n_notes: int = 750):
    timestamps = np.linspace(0, 120, int(n_notes), dtype=np.float64)
    # Include HumanHitSim metadata in the GPU timeline cache key so we avoid collisions with other GPU tests.
    return {
        "metadata": {
            "Song Name": "Timeline Parity Test Song",
            "Difficulty": "Hard",
            "Primary Color": "Beat",
            "Secondary Color": "Flow",
            "Total Notes": int(n_notes),
            "Long Notes": 25,
            "Last Note Time": float(timestamps[-1]),
            "HumanHitSimSeed": 12345,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "full",
        },
        "song_data": {"timestamps": timestamps},
    }


def test_gpu_timeline_matches_cpu_gap_and_activations():
    from gear_optimizer.solver.fever_timeline import get_song_timeline_grid
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    calc_song = _create_mock_song()
    ref_arrays = _create_mock_ref_arrays()

    # CPU reference: minimal 161×161 grids (no per-cell fever_mask copies).
    grid = get_song_timeline_grid(calc_song, ref_arrays)
    cpu_min = grid.to_gpu_arrays_minimal()
    cpu_gap = np.asarray(cpu_min["gap"], dtype=np.int32)
    cpu_fevact = np.asarray(cpu_min["fever_activations"], dtype=np.int32)

    # GPU path: compute and read back the same grids.
    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)
    gpu_gap = np.asarray(gpu_fields.grid_gap.to_numpy()[0], dtype=np.int32)
    gpu_fevact = np.asarray(gpu_fields.grid_fever_activations.to_numpy()[0], dtype=np.int32)

    assert cpu_gap.shape == gpu_gap.shape == (161, 161)
    assert cpu_fevact.shape == gpu_fevact.shape == (161, 161)

    # Exact match (these are integer grids).
    assert np.array_equal(cpu_gap, gpu_gap)
    assert np.array_equal(cpu_fevact, gpu_fevact)
