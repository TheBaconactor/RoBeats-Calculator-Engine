import json
import sqlite3

from gear_optimizer.data.database import ensure_schema
from general_meta.db import get_all_team_buff_loadouts_from_db


def test_get_all_team_buff_loadouts_groups_rows_by_team_buff(monkeypatch, tmp_path):
    db_path = tmp_path / "evolution.db"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    conn.execute(
        "INSERT OR IGNORE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, 0, 0, 0)",
        ("Song A",),
    )

    conn.execute(
        """
        INSERT INTO team_buff_loadouts (
            song_name, team_buff, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s','now'))
        """,
        (
            "Song A",
            "T1",
            "hash1",
            123,
            0,
            json.dumps(["Hat A"]),
            json.dumps(["Mini A"]),
            None,
            None,
        ),
    )

    conn.execute(
        """
        INSERT INTO team_buff_fg_loadouts (
            song_name, team_buff, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s','now'))
        """,
        (
            "Song A",
            "NONE",
            "hash2",
            100,
            999,
            json.dumps(["Hat B"]),
            json.dumps(["Mini B"]),
            None,
            None,
        ),
    )

    conn.commit()
    conn.close()

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    grouped = get_all_team_buff_loadouts_from_db()

    assert "T1" in grouped
    assert "NONE" in grouped
    assert any(r["song_name"] == "Song A" and r["score"] == 123 for r in grouped["T1"])
    assert any(r["song_name"] == "Song A" and r["fg_score"] == 999 for r in grouped["NONE"])
