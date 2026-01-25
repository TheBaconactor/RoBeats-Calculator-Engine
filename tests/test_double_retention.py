from gear_optimizer.data.database import (
    LOADOUTS_PER_SONG_LIMIT,
    get_db_connection,
    init_db,
    save_loadouts_batch,
)


def test_retention_keeps_top_scores_and_best_fg(tmp_path, monkeypatch):
    db_path = tmp_path / "test_double_retention.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    song_name = "Double Retention Test"
    limit = LOADOUTS_PER_SONG_LIMIT

    raw_entries = [
        {
            "score": 2000 + i,
            "fg_score": 0,
            "gear": [f"RawGear{i}"],
            "minis": ["RawMini"],
            "details": {},
            "force": None,
        }
        for i in range(limit)
    ]
    save_loadouts_batch(song_name, raw_entries)

    fg_entry = {
        "score": 500,
        "fg_score": 5000,
        "gear": ["FGGear0"],
        "minis": ["FGMini"],
        "details": {},
        "force": {"score": 5000},
    }
    save_loadouts_batch(song_name, [fg_entry])

    conn = get_db_connection(str(db_path))
    try:
        total = conn.execute(
            "SELECT count(*) FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
            (song_name,),
        ).fetchone()[0]
        count_raw = conn.execute(
            "SELECT count(*) FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5' AND score >= 2000",
            (song_name,),
        ).fetchone()[0]
        count_fg = conn.execute(
            "SELECT count(*) FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5' AND fg_score >= 5000",
            (song_name,),
        ).fetchone()[0]
        fg_total = conn.execute(
            "SELECT count(*) FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5'",
            (song_name,),
        ).fetchone()[0]
    finally:
        conn.close()

    assert count_raw == limit
    # Base leaderboard retains top-N by base score only.
    assert total == limit
    # Best FG is retained in the dedicated FG table.
    assert fg_total == 1
    # And may or may not be present in the base table depending on base score.
    assert count_fg in (0, 1)
