from gear_optimizer.data.database import init_db, save_loadouts_batch
from general_meta.db import get_all_loadouts_from_db


def test_get_all_loadouts_includes_fg_loadouts_rows(monkeypatch, tmp_path):
    db_path = tmp_path / "evolution.db"

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    save_loadouts_batch(
        "Song A",
        [
            {
                "score": 100,
                "fg_score": 999,
                "gear": ["Hat A", "Neck A", "Face A", "Shirt A", "Back A", "Pants A"],
                "minis": ["Mini A", "Mini B", "Mini C"],
                "details": {
                    "Stats": {
                        "Perfect Points": 0,
                        "Combo Multiplier": 0,
                        "Fever Multiplier": 0,
                        "Fever Fill Rate": 0,
                        "Fever Time": 0,
                        "Chill": 0,
                        "Flow": 0,
                        "Rush": 0,
                        "Beat": 0,
                        "Vibe": 0,
                    },
                    "GemCounts": {},
                    "PrimaryColor": "Rush",
                    "SecondaryColor": "Flow",
                    "SelectedElement": "Rush",
                },
                "force": {"Score": 999, "BaseStats": {}, "GemCounts": {}, "ForceGreats": {"config": {"NonFever1": 1}}},
            }
        ],
        team_buff="T5",
    )
    rows = get_all_loadouts_from_db()

    assert any(r["song_name"] == "Song A" and r["fg_score"] == 999 for r in rows)
