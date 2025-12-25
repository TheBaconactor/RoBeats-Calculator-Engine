import os
import sys

import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def _mock_song(*, n_notes: int = 64, duration: float = 120.0) -> dict:
    timestamps = np.linspace(0.0, float(duration), int(n_notes), dtype=np.float32)
    return {
        "metadata": {
            "Song Name": "Contract Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {"timestamps": timestamps},
    }


def _ref_arrays(rows: int) -> dict:
    # Keep deterministic and simple; exact values aren't important for contract checks.
    return {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_solve_best_fever_combination_contract_cpu_gpu():
    """
    Contract test for the public scoring API: required keys/types exist and
    CPU/GPU agree for Score + allocations (small synthetic song).
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.scoring import solve_best_fever_combination

    calc_song = _mock_song()
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)

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

    for res in (cpu_res, gpu_res):
        assert isinstance(res, dict)
        assert isinstance(res.get("Score"), (int, np.integer))
        assert int(res.get("Score")) >= 0
        assert isinstance(res.get("FT"), (int, np.integer))
        assert isinstance(res.get("FF"), (int, np.integer))
        gem_counts = res.get("GemCounts") or {}
        assert isinstance(gem_counts, dict)
        for k in ("Fever Multiplier", "Combo Multiplier", "Perfect Points", "Element"):
            assert isinstance(gem_counts.get(k, 0), (int, np.integer))

    assert int(cpu_res.get("Score", 0)) == int(gpu_res.get("Score", 0))
    assert int(cpu_res.get("FT", -1)) == int(gpu_res.get("FT", -2))
    assert int(cpu_res.get("FF", -1)) == int(gpu_res.get("FF", -2))
    assert (cpu_res.get("GemCounts") or {}) == (gpu_res.get("GemCounts") or {})


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_apply_force_greats_to_result_contract_cpu_gpu():
    """
    Contract test for ForceGreats: FG result must include ForceGreats metadata
    and return a non-negative score on both CPU and GPU (tolerant parity).
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.scoring import solve_best_fever_combination, apply_force_greats_to_result

    calc_song = _mock_song(n_notes=80)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)

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
    cfg_data = {
        "selected_color": "Rush",
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
        override_cfg={**cfg_data, "use_gpu": False},
    )

    fg_cpu = apply_force_greats_to_result(
        data_dict.copy(),
        calc_song,
        ref_arrays,
        use_finder=True,
        use_gpu=False,
    )
    fg_gpu = apply_force_greats_to_result(
        data_dict.copy(),
        calc_song,
        ref_arrays,
        use_finder=True,
        use_gpu=True,
    )

    for fg in (fg_cpu, fg_gpu):
        assert isinstance(fg, dict)
        assert int(fg.get("Score", -1)) >= 0
        meta = fg.get("ForceGreats") or {}
        assert meta.get("enabled") is True
        assert isinstance(meta.get("final_score"), (int, np.integer))

    # Tolerant parity (avoid flakes from f32/searchsorted edge cases).
    assert abs(int(fg_cpu.get("Score", 0)) - int(fg_gpu.get("Score", 0))) <= 5

