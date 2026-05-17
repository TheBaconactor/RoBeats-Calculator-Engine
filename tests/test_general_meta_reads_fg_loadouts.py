from gear_optimizer.data.database import init_db, save_team_buff_loadouts_batch
from general_meta.db import get_all_loadouts_from_db


def _force_payload(fg_score: int, *, base_score: int) -> dict:
    return {
        "Score": int(fg_score),
        "BaseScore": int(base_score),
        "FT": 0,
        "FF": 0,
        "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
        "BaseStats": {
            "Perfect Points": 25,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Fill Rate": 0,
            "Fever Time": 0,
            "Chill": 0,
            "Flow": 0,
            "Rush": 100,
            "Beat": 0,
            "Vibe": 0,
        },
        "Selected Element": "Rush",
        "ForceGreats": {"config": {"NonFever1": 1}, "final_score": int(fg_score)},
    }


def test_get_all_loadouts_includes_fg_loadouts_rows(monkeypatch, tmp_path):
    db_path = tmp_path / "evolution.db"

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    save_team_buff_loadouts_batch(
        "Song A",
        "T5",
        [
            {
                "score": 100,
                "fg_score": 999,
                "gear": ["Hat A", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"],
                "minis": ["Mini A", "Mini B", "Mini C"],
                "details": {"test": "base"},
                "force": _force_payload(999, base_score=100),
            }
        ],
    )
    rows = get_all_loadouts_from_db()

    assert any(r["song_name"] == "Song A" and r["fg_score"] == 999 for r in rows)
