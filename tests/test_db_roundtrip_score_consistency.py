import json

import numpy as np


def _mock_song(*, name: str, n_notes: int = 64, duration: float = 120.0) -> dict:
    timestamps = np.linspace(0.0, float(duration), int(n_notes), dtype=np.float32)
    return {
        "metadata": {
            "Song Name": name,
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


def test_db_roundtrip_base_score_is_self_consistent():
    """
    End-to-end invariant:
    - Solve best gems => (Score, Stats, GemCounts, FT/FF)
    - Save to DB
    - Reload row and re-score from stored Stats

    This catches "score computed from different stats than persisted" drift bugs.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.database import get_db_connection, save_loadouts_batch
    from gear_optimizer.solver.scoring import solve_best_fever_combination
    from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score

    song_name = "pytest_db_roundtrip_base"
    calc_song = _mock_song(name=song_name, n_notes=80)
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
    cfg_data = {
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
        initial_stats=base_stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg_data,
    )
    score = int(res["Score"])

    details = {
        "Stats": {k: int(v) for k, v in (res.get("Stats") or {}).items()},
        "GemCounts": {k: int(v) for k, v in (res.get("GemCounts") or {}).items()},
        "FT": int(res.get("FT", 0)),
        "FF": int(res.get("FF", 0)),
        "Selected Element": str(res.get("Selected Element", "")),
    }

    save_loadouts_batch(
        song_name,
        [
            {
                "score": score,
                "fg_score": 0,
                "gear": ["Test Hat", "Test Neck", "Test Face", "Test Shirt", "Test Back", "Test Pants"],
                "minis": ["Test Mini A", "Test Mini B", "Test Mini C"],
                "details": details,
                "force": None,
            }
        ],
    )

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT score, details_json FROM loadouts WHERE song_name = ? ORDER BY score DESC LIMIT 1",
            (song_name,),
        ).fetchone()

    assert row is not None
    assert int(row["score"]) == score

    stored_details = json.loads(row["details_json"])
    stored_stats = stored_details.get("Stats") or {}
    stored_score = evaluate_stats_score(stored_stats, calc_song, ref_arrays)
    assert int(stored_score) == score
