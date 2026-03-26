import json
from uuid import uuid4

import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = [pytest.mark.gpu, pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")]


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


def _apply_gem_contributions(
    base_stats: dict[str, int],
    gem_counts: dict[str, int],
    selected_color: str,
    ft_gems: int,
    ff_gems: int,
) -> dict[str, int]:
    from gear_optimizer.core.constants import (
        ELEMENTAL_GEM_SCALE,
        GEM_SCALE_FEVER,
        GEM_SCALE_NORMAL,
        GEM_STAT_TO_ELEMENT_SCALE,
    )

    out = {str(k): int(v) for k, v in (base_stats or {}).items()}

    pp = int(gem_counts.get("Perfect Points", 0))
    cm = int(gem_counts.get("Combo Multiplier", 0))
    fm = int(gem_counts.get("Fever Multiplier", 0))
    elem = int(gem_counts.get("Element", 0))

    out["Perfect Points"] = int(out.get("Perfect Points", 0)) + pp * GEM_SCALE_NORMAL
    out["Combo Multiplier"] = int(out.get("Combo Multiplier", 0)) + cm * GEM_SCALE_NORMAL
    out["Fever Multiplier"] = int(out.get("Fever Multiplier", 0)) + fm * GEM_SCALE_FEVER
    out["Fever Time"] = int(out.get("Fever Time", 0)) + int(ft_gems) * GEM_SCALE_FEVER
    out["Fever Fill Rate"] = int(out.get("Fever Fill Rate", 0)) + int(ff_gems) * GEM_SCALE_FEVER

    out["Chill"] = int(out.get("Chill", 0)) + pp * GEM_STAT_TO_ELEMENT_SCALE
    out["Flow"] = int(out.get("Flow", 0)) + cm * GEM_STAT_TO_ELEMENT_SCALE
    out["Rush"] = int(out.get("Rush", 0)) + fm * GEM_STAT_TO_ELEMENT_SCALE
    out["Beat"] = int(out.get("Beat", 0)) + int(ft_gems) * GEM_STAT_TO_ELEMENT_SCALE
    out["Vibe"] = int(out.get("Vibe", 0)) + int(ff_gems) * GEM_STAT_TO_ELEMENT_SCALE
    if selected_color:
        out[str(selected_color)] = int(out.get(str(selected_color), 0)) + elem * ELEMENTAL_GEM_SCALE

    return out


def test_db_roundtrip_force_greats_manual_score_is_self_consistent(tmp_path, monkeypatch):
    """
    End-to-end invariant for manual ForceGreats:
    - Compute base (Score, Stats)
    - Evaluate FG penalties for a fixed config
    - Save to DB with fg_score + force_details_json
    - Reload and recompute FG score from stored (Stats + config)
    """
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch
    from gear_optimizer.solver.scoring.force_greats import _extract_base_stats
    from gear_optimizer.solver.scoring.stats_scoring import evaluate_stats_score
    from gear_optimizer.solver.scoring import solve_best_fever_combination
    from gear_optimizer.solver.scoring.force_greats import evaluate_force_greats

    song_name = f"pytest_db_roundtrip_fg_manual_{uuid4().hex}"
    calc_song = _mock_song(name=song_name, n_notes=96)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    db_path = tmp_path / "db_roundtrip_fg_manual.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

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
        "use_gpu": True,
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
    assert score > 0

    details = {
        "Stats": {k: int(v) for k, v in (res.get("Stats") or {}).items()},
        "GemCounts": {k: int(v) for k, v in (res.get("GemCounts") or {}).items()},
        "FT": int(res.get("FT", 0)),
        "FF": int(res.get("FF", 0)),
        "SelectedElement": str(res.get("Selected Element", "")),
    }
    force_data = {"ForceGreats": {"mode": "manual", "config": fg_eval["config_dict"]}}

    # Phase 1 (in-house): verify score math and backward/forward stat accounting.
    inhouse_stats = {k: int(v) for k, v in (details.get("Stats") or {}).items()}
    inhouse_base_score = int(evaluate_stats_score(inhouse_stats, calc_song, ref_arrays))
    assert abs(inhouse_base_score - score) <= 2

    inhouse_counts = _config_dict_to_counts(fg_eval["config_dict"])
    inhouse_fg_eval = evaluate_force_greats(inhouse_stats, calc_song, ref_arrays, inhouse_counts)
    assert inhouse_fg_eval is not None
    assert int(inhouse_fg_eval["final_score"]) == fg_score

    inhouse_gems = details.get("GemCounts") or {}
    inhouse_ft = int(details.get("FT") or 0)
    inhouse_ff = int(details.get("FF") or 0)
    inhouse_selected = str(details.get("SelectedElement") or "")
    inhouse_base_stats = _extract_base_stats(
        inhouse_stats,
        inhouse_gems,
        inhouse_selected,
        inhouse_ft,
        inhouse_ff,
    )
    inhouse_forward = _apply_gem_contributions(
        inhouse_base_stats,
        inhouse_gems,
        inhouse_selected,
        inhouse_ft,
        inhouse_ff,
    )
    assert inhouse_forward == inhouse_stats

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

    with get_db_connection(str(db_path)) as conn:
        row = conn.execute(
            "SELECT score, fg_score, details_json, force_details_json "
            "FROM team_buff_loadouts WHERE song_name = ? AND team_buff = 'T5' ORDER BY score DESC LIMIT 1",
            (song_name,),
        ).fetchone()

    assert row is not None
    assert int(row["score"]) == score
    assert int(row["fg_score"]) == fg_score

    from gear_optimizer.data.database import _unpack_stats_after_load

    stored_details = _unpack_stats_after_load(json.loads(row["details_json"])) or {}
    stored_force = json.loads(row["force_details_json"])
    cfg = (stored_force.get("ForceGreats") or {}).get("config") or {}
    counts = _config_dict_to_counts(cfg)
    assert counts == forced_counts

    stored_stats = stored_details.get("Stats") or {}
    stored_base_score = int(evaluate_stats_score(stored_stats, calc_song, ref_arrays))
    assert abs(stored_base_score - int(row["score"])) <= 2

    fg_eval_roundtrip = evaluate_force_greats(stored_stats, calc_song, ref_arrays, counts)
    assert fg_eval_roundtrip is not None
    assert int(fg_eval_roundtrip["final_score"]) == fg_score

    # Phase 2 (persistence): work backwards, then add contributions back and verify exact stat restoration.
    stored_gems = stored_details.get("GemCounts") or {}
    stored_ft = int(stored_details.get("FT") or 0)
    stored_ff = int(stored_details.get("FF") or 0)
    stored_selected = str(
        stored_details.get("SelectedElement")
        or stored_details.get("Selected Element")
        or ""
    )
    stored_base_stats = _extract_base_stats(
        stored_stats,
        stored_gems,
        stored_selected,
        stored_ft,
        stored_ff,
    )
    stored_forward = _apply_gem_contributions(
        stored_base_stats,
        stored_gems,
        stored_selected,
        stored_ft,
        stored_ff,
    )
    assert stored_forward == {k: int(v) for k, v in stored_stats.items()}
