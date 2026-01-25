import sqlite3


def test_frontend_views_exist(tmp_path):
    # Use an isolated DB to ensure migrations run end-to-end.
    from gear_optimizer.data.migrations import ensure_schema

    db_path = tmp_path / "evolution.db"
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)
        views = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view';").fetchall()}
        assert "fg_loadouts_unified" in views
        assert "loadouts_unified" in views
        assert "frontend_best_base_loadouts" in views
        assert "frontend_best_fg_loadouts" in views
        assert "frontend_base_top51_by_song_tier" in views
        assert "frontend_fg_top51_by_song_tier" in views
    finally:
        conn.close()
