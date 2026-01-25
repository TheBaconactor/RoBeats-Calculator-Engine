import sqlite3


def test_schema_v15_creates_frontend_views_and_unified_behavior(tmp_path):
    from gear_optimizer.data import migrations

    db_path = tmp_path / "test_frontend_views.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        migrations.ensure_schema(conn)
        assert migrations.get_schema_version(conn) == migrations.LATEST_SCHEMA_VERSION

        views = {
            r["name"]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
            if r and r["name"]
        }
        required = {
            "fg_loadouts_unified",
            "loadouts_unified",
            "frontend_best_base_loadouts",
            "frontend_best_fg_loadouts",
            "frontend_base_top51_by_song_tier",
            "frontend_fg_top51_by_song_tier",
        }
        assert required.issubset(views)

        # Song A: explicit tier row exists, so legacy `loadouts` row is excluded from loadouts_unified.
        song_a = "Insight (Hard) by Haywyre"
        conn.execute("INSERT INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, 0, 0, 0)", (song_a,))
        conn.execute(
            """
            INSERT INTO loadouts (song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp)
            VALUES (?, ?, ?, ?, '[]', '[]', '{}', NULL, 1)
            """,
            (song_a, "legacyhash", 10, 0),
        )
        conn.execute(
            """
            INSERT INTO team_buff_loadouts (
                song_name, team_buff, loadout_hash, score, fg_score,
                gear_json, minis_json, details_json, force_details_json, timestamp
            )
            VALUES (?, 'T5', ?, ?, ?, '[]', '[]', '{}', NULL, 2)
            """,
            (song_a, "tierhash", 20, 0),
        )

        row = conn.execute(
            "SELECT team_buff, loadout_hash, score, source_table FROM loadouts_unified WHERE song_name = ?",
            (song_a,),
        ).fetchone()
        assert dict(row) == {
            "team_buff": "T5",
            "loadout_hash": "tierhash",
            "score": 20,
            "source_table": "team_buff_loadouts",
        }

        # Song B: no tier rows exist, so legacy loadouts row is surfaced as implicit T5.
        song_b = "Some Song (Normal) by Someone"
        conn.execute("INSERT INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, 0, 0, 0)", (song_b,))
        conn.execute(
            """
            INSERT INTO loadouts (song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp)
            VALUES (?, ?, ?, ?, '[]', '[]', '{}', NULL, 1)
            """,
            (song_b, "legacyhash2", 11, 0),
        )

        row = conn.execute(
            "SELECT team_buff, loadout_hash, score, source_table FROM loadouts_unified WHERE song_name = ?",
            (song_b,),
        ).fetchone()
        assert dict(row) == {"team_buff": "T5", "loadout_hash": "legacyhash2", "score": 11, "source_table": "loadouts"}

        # Title/difficulty parsing should follow the standard "(Hard) by" form.
        row = conn.execute(
            """
            SELECT song_title, difficulty
            FROM frontend_base_top51_by_song_tier
            WHERE song_name = ?
            LIMIT 1
            """,
            (song_a,),
        ).fetchone()
        assert dict(row) == {"song_title": "Insight", "difficulty": "Hard"}
    finally:
        conn.close()
