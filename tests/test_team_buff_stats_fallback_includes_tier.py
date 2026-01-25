import json
import sqlite3
from pathlib import Path


def test_team_buff_stats_fallback_includes_tier_effect(monkeypatch, tmp_path: Path):
    """
    Regression: when a tier entry is persisted with missing/empty details['Stats'],
    the fallback Stats computation must include the TeamBuff tier PP/element effect.
    """
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    from gear_optimizer.data.database import init_db, save_team_buff_loadouts_batch

    init_db()

    # Minimal entry: no gear/minis, no gems. Stats should be exactly the TeamBuff effect.
    entry = {
        "score": 123,
        "fg_score": 0,
        "gear": [],
        "minis": [],
        "details": {
            "Stats": {},  # triggers fallback
            "GemCounts": {},
            "FT": 0,
            "FF": 0,
            "SelectedElement": "Rush",
            "PrimaryColor": "Rush",
            "SecondaryColor": "Flow",
        },
        "force": None,
    }

    save_team_buff_loadouts_batch("pytest_song", "T10", [entry])

    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff=? LIMIT 1",
            ("pytest_song", "T10"),
        ).fetchone()
        assert row is not None
        details = json.loads(row[0])
        stats = details.get("Stats") or {}
        assert stats.get("Perfect Points") == 20
        assert stats.get("Rush") == 25
    finally:
        con.close()

