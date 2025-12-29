from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from gear_optimizer.data.db_merge import merge_databases


def _init_minimal_schema(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS songs (
                name TEXT PRIMARY KEY,
                best_score INTEGER DEFAULT 0,
                best_fg_score INTEGER DEFAULT 0,
                last_updated REAL
            );
            CREATE TABLE IF NOT EXISTS loadouts (
                song_name TEXT,
                loadout_hash TEXT,
                score INTEGER,
                fg_score INTEGER DEFAULT 0,
                gear_json TEXT,
                minis_json TEXT,
                details_json TEXT,
                force_details_json TEXT,
                timestamp REAL,
                PRIMARY KEY (song_name, loadout_hash)
            );
            CREATE TABLE IF NOT EXISTS fg_loadouts (
                song_name TEXT,
                loadout_hash TEXT,
                score INTEGER,
                fg_score INTEGER,
                gear_json TEXT,
                minis_json TEXT,
                details_json TEXT,
                force_details_json TEXT,
                timestamp REAL,
                PRIMARY KEY (song_name, loadout_hash)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_merge_databases_includes_fg_loadouts(tmp_path: Path) -> None:
    """
    Regression test:
    Ensure DB merge imports FG leaderboard entries from `fg_loadouts` (even if the
    hash is not present in `loadouts`).
    """
    song = "Merge Test Song"
    main_db = tmp_path / "main.db"
    secondary_db = tmp_path / "secondary.db"

    _init_minimal_schema(main_db)
    _init_minimal_schema(secondary_db)

    # Main DB: song exists, but has no FG leaderboard entry.
    conn = sqlite3.connect(str(main_db))
    try:
        conn.execute(
            "INSERT INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            (song, 100, 0, 0.0),
        )
        conn.commit()
    finally:
        conn.close()

    # Secondary DB: contains an FG-only entry.
    fg_hash = "hash_fg_only"
    gear_json = json.dumps(["Hat1", "Neck1"])
    minis_json = json.dumps(["Mini1", "Mini2", "Mini3"])
    details_json = json.dumps({"Score": 80})
    force_json = json.dumps({"ForceGreats": {"config": {"NonFever1": 3, "NonFever2": 0}, "final_score": 150}})

    conn = sqlite3.connect(str(secondary_db))
    try:
        conn.execute(
            "INSERT INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            (song, 90, 150, 0.0),
        )
        conn.execute(
            """
            INSERT INTO fg_loadouts (
                song_name, loadout_hash, score, fg_score, gear_json, minis_json,
                details_json, force_details_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (song, fg_hash, 80, 150, gear_json, minis_json, details_json, force_json, 0.0),
        )
        conn.commit()
    finally:
        conn.close()

    success, message, stats = merge_databases(
        str(main_db),
        str(secondary_db),
        delete_after_merge=False,
        backup_before_merge=False,
    )
    assert success, message
    assert stats.get("fg_loadouts_added", 0) == 1

    # Verify FG row and song best_fg_score imported into main DB.
    conn = sqlite3.connect(str(main_db))
    try:
        cur = conn.execute("SELECT best_fg_score FROM songs WHERE name=?", (song,))
        assert cur.fetchone()[0] == 150

        cur = conn.execute(
            "SELECT loadout_hash, score, fg_score FROM fg_loadouts WHERE song_name=?",
            (song,),
        )
        rows = cur.fetchall()
        assert rows == [(fg_hash, 80, 150)]
    finally:
        conn.close()
