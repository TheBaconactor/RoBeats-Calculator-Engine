import numpy as np


def _mock_song(*, n_notes: int = 64, duration: float = 90.0) -> dict:
    timestamps = np.linspace(0.0, float(duration), int(n_notes), dtype=np.float32)
    return {
        "metadata": {
            "Song Name": "FeverStats Song",
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
    return {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }


def test_solve_best_fever_combination_stats_include_gem_contributions():
    """
    Regression: result['Stats'] must include the same primary-stat gem contributions
    used to compute the score (PP/CM/FM), otherwise persisted DB/UI stats drift.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS, GEM_SCALE_NORMAL, GEM_SCALE_FEVER
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
    cfg = {
        "selected_color": "Rush",
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
        "use_gpu": False,
    }

    res = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats.copy(),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg,
    )

    gems = res.get("GemCounts") or {}
    stats = res.get("Stats") or {}

    g_pp = int(gems.get("Perfect Points", 0))
    g_cm = int(gems.get("Combo Multiplier", 0))
    g_fm = int(gems.get("Fever Multiplier", 0))

    assert int(stats.get("Perfect Points", -1)) == int(base_stats["Perfect Points"]) + g_pp * GEM_SCALE_NORMAL
    assert int(stats.get("Combo Multiplier", -1)) == int(base_stats["Combo Multiplier"]) + g_cm * GEM_SCALE_NORMAL
    assert int(stats.get("Fever Multiplier", -1)) == int(base_stats["Fever Multiplier"]) + g_fm * GEM_SCALE_FEVER

