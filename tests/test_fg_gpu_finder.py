import os
import sys
import numpy as np
import pytest

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_fg_finder_gpu_tolerant_parity():
    """
    Tolerant parity test for the full GPU ForceGreatsFinder path.
    We allow small differences vs CPU due to f32/searchsorted edge cases.
    """
    try:
        import taichi as _  # noqa: F401
    except Exception:
        pytest.skip("Taichi not available")

    from gear_optimizer.solver.scoring import (
        solve_best_fever_combination,
        apply_force_greats_to_result,
        FG_CACHE,
        FEVER_TIMELINE_CACHE,
    )
    from gear_optimizer.core.constants import TOTAL_ROWS

    # Mock song
    timestamps = np.linspace(0.0, 120.0, 100, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "FG GPU Finder Test Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 120.0,
            "Total Notes": 100,
        },
        "song_data": {"timestamps": timestamps},
    }

    # Base stats (kept simple/deterministic)
    base_stats_fixed = {
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
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }

    cfg_data = {
        "selected_color": "Rush",
        "use_gpu": False,
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }

    data_dict = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats_fixed,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg_data,
    )

    # Clear caches so both paths do real work
    FG_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()

    fg_cpu = apply_force_greats_to_result(
        data_dict.copy(),
        calc_song,
        ref_arrays,
        use_finder=True,
        use_gpu=False,
    )
    assert fg_cpu is not None
    assert fg_cpu.get("ForceGreats", {}).get("enabled") is True
    assert fg_cpu.get("ForceGreats", {}).get("algo_version") == 3

    FG_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()

    fg_gpu = apply_force_greats_to_result(
        data_dict.copy(),
        calc_song,
        ref_arrays,
        use_finder=True,
        use_gpu=True,
    )
    assert fg_gpu is not None
    assert fg_gpu.get("ForceGreats", {}).get("enabled") is True
    assert fg_gpu.get("ForceGreats", {}).get("algo_version") == 3

    cpu_score = int(fg_cpu.get("Score", 0))
    gpu_score = int(fg_gpu.get("Score", 0))

    # Tolerant: allow small drift
    assert abs(cpu_score - gpu_score) <= 5


