import json
import sqlite3

from gear_optimizer.data.database import ensure_schema
from gear_optimizer.general_meta import get_all_loadouts_from_db


def test_get_all_loadouts_includes_fg_loadouts_rows(monkeypatch, tmp_path):
    db_path = tmp_path / "evolution.db"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    conn.execute(
        "INSERT OR IGNORE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, 0, 0, 0)",
        ("Song A",),
    )

    # Only insert into fg_loadouts (simulates older/merged DBs where the best FG rows may
    # not be reflected in the base `loadouts` table the way we expect).
    conn.execute(
        """
        INSERT INTO fg_loadouts (song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, strftime('%s','now'))
        """,
        (
            "Song A",
            "hash1",
            100,
            999,
            json.dumps(["Hat A"]),
            json.dumps(["Mini A"]),
            None,
            None,
        ),
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    rows = get_all_loadouts_from_db()

    assert any(r["song_name"] == "Song A" and r["fg_score"] == 999 for r in rows)
