"""
GPU timeline parity test.

Verifies that GPU-uploaded timeline fields match the exact startup-built
frontier payload used by runtime scoring.
"""

import os
import sys

import numpy as np
import pytest

# Add repo root to path for imports.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module", autouse=True)
def _taichi_ready():
    pytest.importorskip("taichi")
    try:
        from gear_optimizer.solver.taichi_gem.runtime import init_taichi

        init_taichi()
    except Exception as exc:
        pytest.skip(f"Taichi init failed: {exc}")


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
    # Include timing-envelope metadata in the GPU timeline cache key so we avoid collisions with other GPU tests.
    return {
        "metadata": {
            "Song Name": "Timeline Parity Test Song",
            "Difficulty": "Hard",
            "Primary Color": "Beat",
            "Secondary Color": "Flow",
            "Total Notes": int(n_notes),
            "Long Notes": 25,
            "Last Note Time": float(timestamps[-1]),
            "TimingEnvelopeApplied": True,
            "TimingEnvelopeMode": "perfect",
            "TimingEnvelopeFGCarry": "full",
        },
        "song_data": {
            "timestamps": timestamps,
            "note_types": np.ones(int(n_notes), dtype=np.int16),
            "lanes": np.arange(int(n_notes), dtype=np.int32) % np.int32(4),
        },
    }


def test_gpu_timeline_matches_cpu_gap_and_activations(monkeypatch, tmp_path):
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        precompute_timeline_gpu,
    )
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path / "timeline_frontier_cache"))
    calc_song = _create_mock_song()
    apply_timing_envelope(calc_song, mode="perfect_window")
    ref_arrays = _create_mock_ref_arrays()

    prebuilt_frontier = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    cpu_gap = np.asarray(prebuilt_frontier.payload.grid_gap[0], dtype=np.int32)
    cpu_fevact = np.asarray(prebuilt_frontier.payload.grid_fever_activations[0], dtype=np.int32)

    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0, prebuilt_frontier=prebuilt_frontier)
    gpu_gap = np.asarray(gpu_fields.grid_gap.to_numpy()[0], dtype=np.int32)
    gpu_fevact = np.asarray(gpu_fields.grid_fever_activations.to_numpy()[0], dtype=np.int32)

    assert cpu_gap.shape == gpu_gap.shape == (161, 161)
    assert cpu_fevact.shape == gpu_fevact.shape == (161, 161)
    assert np.array_equal(cpu_gap, gpu_gap)
    assert np.array_equal(cpu_fevact, gpu_fevact)
