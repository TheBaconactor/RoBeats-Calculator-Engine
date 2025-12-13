import os
import sys

import numpy as np
import pytest

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_population_aggregation_smoke():
    """
    Smoke test: GPU aggregation path should run without crashing and preserve scoring parity.

    We don't assert speed here—just correctness vs CPU aggregation.
    """
    from gear_optimizer.solver.scoring import batch_evaluate_genomes
    from gear_optimizer.core.constants import TOTAL_ROWS

    # Minimal 2-genome population (dict items like real GA)
    genomes = [
        [{"Name": "Hat_A", "type": "Hat", "Perfect Points": 10, "Beat": 100}],
        [{"Name": "Hat_B", "type": "Hat", "Perfect Points": 20, "Beat": 200}],
    ]

    base_stats_fixed = {
        "Perfect Points": 50,
        "Combo Multiplier": 50,
        "Fever Multiplier": 50,
        "Fever Fill Rate": 50,
        "Fever Time": 50,
        "Rush": 50,
        "Flow": 50,
        "Beat": 50,
        "Vibe": 50,
        "Chill": 50,
    }

    timestamps = np.linspace(0.0, 120.0, 120, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "GPU Aggregate Smoke Song",
            "Difficulty": "Hard",
            "Primary Color": "Beat",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {"timestamps": timestamps},
    }

    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }

    cfg_cpu = {
        "selected_color": "Beat",
        "use_gpu": True,  # still use GPU gem solver to keep paths consistent
        "gpu_aggregate_stats": False,
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }

    cfg_gpuagg = {**cfg_cpu, "gpu_aggregate_stats": True}

    res_cpu = batch_evaluate_genomes(genomes, base_stats_fixed, cfg_cpu, calc_song, ref_arrays)
    res_gpuagg = batch_evaluate_genomes(genomes, base_stats_fixed, cfg_gpuagg, calc_song, ref_arrays)

    assert len(res_cpu) == len(res_gpuagg) == 2
    assert res_cpu[0]["Score"] == res_gpuagg[0]["Score"]
    assert res_cpu[1]["Score"] == res_gpuagg[1]["Score"]






