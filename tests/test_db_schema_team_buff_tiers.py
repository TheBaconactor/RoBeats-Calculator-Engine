import sqlite3


def test_db_schema_includes_team_buff_tier_tables():
    from gear_optimizer.data.migrations import LATEST_SCHEMA_VERSION, ensure_schema

    conn = sqlite3.connect(":memory:")
    try:
        ensure_schema(conn)
        version = int(conn.execute("PRAGMA user_version;").fetchone()[0] or 0)
        assert version == int(LATEST_SCHEMA_VERSION)

        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        tables = {r[0] for r in rows or []}
        assert "team_buff_loadouts" in tables
        assert "team_buff_fg_loadouts" in tables
    finally:
        conn.close()
