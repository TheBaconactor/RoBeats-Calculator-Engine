import numpy as np

from gear_optimizer.solver.scoring.force_greats import evaluate_force_greats


def test_force_greats_body_penalty_matches_full_combo_flooring_regression() -> None:
    """
    Regression for a small but real score drift caused by Great penalty flooring at full combo.

    When forced greats occur beyond the first 100 notes, the score penalty uses a constant
    full-combo body penalty. This must match the game's floor-after-multiply behavior.
    """

    rows = 161  # TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.zeros(rows, dtype=np.float64),
        "Combo Multiplier": np.ones(rows, dtype=np.float64),
        "Fever Multiplier": np.ones(rows, dtype=np.float64),
        "Fever Fill Rate": np.zeros(rows, dtype=np.float64),
        "Fever Time": np.zeros(rows, dtype=np.float64),
    }
    ref_arrays["Perfect Points"][25] = 308.0
    ref_arrays["Combo Multiplier"][56] = 2.498220087
    # Force two non-fever sections; ensure section 2 starts at note index > 100.
    ref_arrays["Fever Fill Rate"][0] = 1.65
    ref_arrays["Fever Time"][0] = 0.01

    timestamps = np.arange(0.0, 200.0, dtype=np.float64)
    calc_song = {
        "metadata": {
            "Song Name": "FG Body Penalty Regression Song",
            "Primary Color": "Chill",
            "Secondary Color": "Chill",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }

    stats = {
        "Perfect Points": 25,
        "Combo Multiplier": 56,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Chill": 770,
        "Vibe": 0,
        "Beat": 0,
        "Flow": 0,
        "Rush": 0,
    }

    # Only section 2 has forced greats; with section2 start >100 this uses the full-combo body penalty.
    forced_counts = [0, 19]
    res = evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts)
    assert res is not None

    # Expected body penalty for this setup: 2 points lower per forced great than the buggy computation.
    assert res["penalty_analysis"]["NonFever2"]["score_penalty"] == 19 * 2319

