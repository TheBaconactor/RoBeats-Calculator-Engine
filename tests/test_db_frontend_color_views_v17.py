import sqlite3


def test_schema_v17_adds_color_views_and_keeps_canonical_unified_filtered(tmp_path):
    from gear_optimizer.data import migrations

    db_path = tmp_path / "test_frontend_color_views.db"
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
            "loadouts_color_unified",
            "fg_loadouts_color_unified",
            "frontend_base_top51_by_song_tier_color",
            "frontend_fg_top51_by_song_tier_color",
        }
        assert required.issubset(views)

        song = "Color Buff Song (Hard) by UnitTest"
        conn.execute("INSERT INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, 0, 0, 0)", (song,))

        conn.execute(
            """
            INSERT INTO team_buff_loadouts (
                song_name, team_buff, loadout_hash, score, fg_score,
                gear_json, minis_json, details_json, force_details_json, timestamp
            )
            VALUES (?, ?, ?, ?, 0, '[]', '[]', '{}', NULL, 10)
            """,
            (song, "T5", "hash_primary", 100),
        )
        conn.execute(
            """
            INSERT INTO team_buff_loadouts (
                song_name, team_buff, loadout_hash, score, fg_score,
                gear_json, minis_json, details_json, force_details_json, timestamp
            )
            VALUES (?, ?, ?, ?, 0, '[]', '[]', '{}', NULL, 10)
            """,
            (song, "T5__SECONDARY", "hash_secondary", 95),
        )
        conn.execute(
            """
            INSERT INTO team_buff_loadouts (
                song_name, team_buff, loadout_hash, score, fg_score,
                gear_json, minis_json, details_json, force_details_json, timestamp
            )
            VALUES (?, ?, ?, ?, 0, '[]', '[]', '{}', NULL, 10)
            """,
            (song, "T5__NONE", "hash_none", 90),
        )

        canonical_rows = conn.execute(
            "SELECT team_buff, loadout_hash FROM loadouts_unified WHERE song_name = ? ORDER BY team_buff, loadout_hash",
            (song,),
        ).fetchall()
        assert [dict(r) for r in canonical_rows] == [{"team_buff": "T5", "loadout_hash": "hash_primary"}]

        color_rows = conn.execute(
            """
            SELECT team_buff, color_buff, loadout_hash, score
            FROM loadouts_color_unified
            WHERE song_name = ?
            ORDER BY color_buff
            """,
            (song,),
        ).fetchall()
        assert [dict(r) for r in color_rows] == [
            {"team_buff": "T5", "color_buff": "NONE", "loadout_hash": "hash_none", "score": 90},
            {"team_buff": "T5", "color_buff": "PRIMARY", "loadout_hash": "hash_primary", "score": 100},
            {"team_buff": "T5", "color_buff": "SECONDARY", "loadout_hash": "hash_secondary", "score": 95},
        ]

        conn.execute(
            """
            INSERT INTO team_buff_fg_loadouts (
                song_name, team_buff, loadout_hash, score, fg_score,
                gear_json, minis_json, details_json, force_details_json, timestamp
            )
            VALUES (?, ?, ?, ?, ?, '[]', '[]', '{}', '{}', 10)
            """,
            (song, "T5", "fghash_primary", 100, 130),
        )
        conn.execute(
            """
            INSERT INTO team_buff_fg_loadouts (
                song_name, team_buff, loadout_hash, score, fg_score,
                gear_json, minis_json, details_json, force_details_json, timestamp
            )
            VALUES (?, ?, ?, ?, ?, '[]', '[]', '{}', '{}', 10)
            """,
            (song, "T5__SECONDARY", "fghash_secondary", 95, 128),
        )

        fg_canonical_rows = conn.execute(
            "SELECT team_buff, loadout_hash FROM fg_loadouts_unified WHERE song_name = ? ORDER BY team_buff, loadout_hash",
            (song,),
        ).fetchall()
        assert [dict(r) for r in fg_canonical_rows] == [{"team_buff": "T5", "loadout_hash": "fghash_primary"}]

        fg_color_rows = conn.execute(
            """
            SELECT team_buff, color_buff, loadout_hash, fg_score
            FROM fg_loadouts_color_unified
            WHERE song_name = ?
            ORDER BY color_buff
            """,
            (song,),
        ).fetchall()
        assert [dict(r) for r in fg_color_rows] == [
            {"team_buff": "T5", "color_buff": "PRIMARY", "loadout_hash": "fghash_primary", "fg_score": 130},
            {"team_buff": "T5", "color_buff": "SECONDARY", "loadout_hash": "fghash_secondary", "fg_score": 128},
        ]

        fg_frontend_rows = conn.execute(
            """
            SELECT team_buff, color_buff, rank, loadout_hash
            FROM frontend_fg_top51_by_song_tier_color
            WHERE song_name = ?
            ORDER BY color_buff, rank
            """,
            (song,),
        ).fetchall()
        assert [dict(r) for r in fg_frontend_rows] == [
            {"team_buff": "T5", "color_buff": "PRIMARY", "rank": 1, "loadout_hash": "fghash_primary"},
            {"team_buff": "T5", "color_buff": "SECONDARY", "rank": 1, "loadout_hash": "fghash_secondary"},
        ]
    finally:
        conn.close()
