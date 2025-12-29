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


pytestmark = pytest.mark.gpu


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gem_solver_cpu_gpu_exact_parity_smoke():
    """
    Minimal CPU↔GPU parity harness for the gem solver.

    This uses the public orchestration API (solve_best_fever_combination) to ensure:
    - identical Score
    - identical gem allocations (FT/FF + GemCounts)
    """
    from gear_optimizer.solver.scoring import solve_best_fever_combination
    from gear_optimizer.core.constants import TOTAL_ROWS

    timestamps = np.linspace(0.0, 120.0, 120, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "Parity Smoke Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {"timestamps": timestamps},
    }

    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }

    base_stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 95,
        "Fever Multiplier": 90,
        "Fever Fill Rate": 80,
        "Fever Time": 85,
        "Rush": 140,
        "Flow": 120,
        "Beat": 60,
        "Vibe": 60,
        "Chill": 60,
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

    cpu_res = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats.copy(),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg={**base_cfg, "use_gpu": False},
    )
    gpu_res = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats.copy(),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg={**base_cfg, "use_gpu": True},
    )

    assert int(cpu_res.get("Score", 0)) == int(gpu_res.get("Score", 0))
    assert int(cpu_res.get("FT", -1)) == int(gpu_res.get("FT", -2))
    assert int(cpu_res.get("FF", -1)) == int(gpu_res.get("FF", -2))
    assert (cpu_res.get("GemCounts") or {}) == (gpu_res.get("GemCounts") or {})


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_force_greats_finder_cpu_gpu_tolerant_parity_smoke():
    """
    Minimal CPU↔GPU parity harness for ForceGreatsFinder (hill-climb path).

    We allow a small tolerance due to f32/searchsorted edge cases.
    """
    from gear_optimizer.solver.scoring import (
        solve_best_fever_combination,
        apply_force_greats_to_result,
        FG_CACHE,
        FEVER_TIMELINE_CACHE,
    )
    from gear_optimizer.core.constants import TOTAL_ROWS

    timestamps = np.linspace(0.0, 120.0, 100, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "FG Parity Smoke Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
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
        initial_stats=base_stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg_data,
    )

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

    cpu_score = int(fg_cpu.get("Score", 0))
    gpu_score = int(fg_gpu.get("Score", 0))

    assert abs(cpu_score - gpu_score) <= 5
