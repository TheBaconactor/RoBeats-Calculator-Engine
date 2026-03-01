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


def _config_dict_to_counts(cfg: dict) -> list[int]:
    if not cfg:
        return []
    pairs = []
    for k, v in cfg.items():
        if not isinstance(k, str) or not k.startswith("NonFever"):
            continue
        try:
            idx = int(k.replace("NonFever", "")) - 1
        except Exception:
            continue
        pairs.append((idx, int(v)))
    if not pairs:
        return []
    pairs.sort(key=lambda x: x[0])
    max_idx = pairs[-1][0]
    out = [0] * (max_idx + 1)
    for idx, v in pairs:
        if 0 <= idx < len(out):
            out[idx] = max(0, int(v))
    return out


def test_db_roundtrip_force_greats_manual_score_is_self_consistent():
    """
    End-to-end invariant for manual ForceGreats:
    - Compute base (Score, Stats)
    - Evaluate FG penalties for a fixed config
    - Save to DB with fg_score + force_details_json
    - Reload and recompute FG score from stored (Stats + config)
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.database import get_db_connection, save_loadouts_batch
    from gear_optimizer.solver.scoring import solve_best_fever_combination
    from gear_optimizer.solver.scoring.force_greats import evaluate_force_greats

    song_name = "pytest_db_roundtrip_fg_manual"
    calc_song = _mock_song(name=song_name, n_notes=96)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)

    base_stats = {
        "Perfect Points": 90,
        "Combo Multiplier": 110,
        "Fever Multiplier": 120,
        "Fever Fill Rate": 70,
        "Fever Time": 90,
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

    forced_counts = [2, 0]
    fg_eval = evaluate_force_greats(res["Stats"], calc_song, ref_arrays, forced_counts)
    assert fg_eval is not None

    score = int(res["Score"])
    fg_score = int(fg_eval["final_score"])

    details = {
        "Stats": {k: int(v) for k, v in (res.get("Stats") or {}).items()},
        "GemCounts": {k: int(v) for k, v in (res.get("GemCounts") or {}).items()},
        "FT": int(res.get("FT", 0)),
        "FF": int(res.get("FF", 0)),
        "Selected Element": str(res.get("Selected Element", "")),
        "PrimaryColor": str(calc_song["metadata"].get("Primary Color", "")),
        "SecondaryColor": str(calc_song["metadata"].get("Secondary Color", "")),
    }
    force_data = {"ForceGreats": {"mode": "manual", "config": fg_eval["config_dict"]}}

    save_loadouts_batch(
        song_name,
        [
            {
                "score": score,
                "fg_score": fg_score,
                "gear": ["Test Hat", "Test Neck", "Test Face", "Test Shirt", "Test Back", "Test Pants"],
                "minis": ["Test Mini A", "Test Mini B", "Test Mini C"],
                "details": details,
                "force": force_data,
            }
        ],
    )

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT score, fg_score, details_json, force_details_json "
            "FROM team_buff_loadouts WHERE song_name = ? AND team_buff = 'T5' LIMIT 1",
            (song_name,),
        ).fetchone()

    assert row is not None
    assert int(row["score"]) == score
    assert int(row["fg_score"]) == fg_score

    stored_details = json.loads(row["details_json"])
    stored_force = json.loads(row["force_details_json"])
    cfg = (stored_force.get("ForceGreats") or {}).get("config") or {}
    counts = _config_dict_to_counts(cfg)
    assert counts == forced_counts

    stored_stats = stored_details.get("Stats") or {}
    fg_eval_roundtrip = evaluate_force_greats(stored_stats, calc_song, ref_arrays, counts)
    assert fg_eval_roundtrip is not None
    assert int(fg_eval_roundtrip["final_score"]) == fg_score
