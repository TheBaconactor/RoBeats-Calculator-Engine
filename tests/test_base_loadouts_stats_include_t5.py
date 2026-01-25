import json
import sqlite3
from pathlib import Path


def test_base_loadouts_stats_include_team_buff_t5(monkeypatch, tmp_path: Path):
    """
    Regression: base (non-tier) persistence is treated as TeamBuff auto-mode (T5).
    If we persist loadout-only Stats, consumers that assume base==T5 will render T5 like NONE.
    """
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    from gear_optimizer.data.database import init_db, save_loadouts_batch

    init_db()

    entry = {
        "score": 123,
        "fg_score": 0,
        "gear": [],
        "minis": [],
        "details": {
            "Stats": {},  # triggers recompute
            "GemCounts": {},
            "FT": 0,
            "FF": 0,
            "SelectedElement": "Rush",
            "PrimaryColor": "Rush",
            "SecondaryColor": "Flow",
        },
        "force": None,
    }

    save_loadouts_batch("pytest_song", [entry])

    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5' LIMIT 1",
            ("pytest_song",),
        ).fetchone()
        assert row is not None
        details = json.loads(row[0])
        stats = details.get("Stats") or {}
        assert stats.get("Perfect Points") == 25
        assert stats.get("Rush") == 30
    finally:
        con.close()
