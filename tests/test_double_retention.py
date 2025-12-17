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
            "SELECT count(*) FROM loadouts WHERE song_name=?", (song_name,)
        ).fetchone()[0]
        count_raw = conn.execute(
            "SELECT count(*) FROM loadouts WHERE song_name=? AND score >= 2000",
            (song_name,),
        ).fetchone()[0]
        count_fg = conn.execute(
            "SELECT count(*) FROM loadouts WHERE song_name=? AND fg_score >= 5000",
            (song_name,),
        ).fetchone()[0]
    finally:
        conn.close()

    assert count_raw == limit
    assert count_fg == 1
    assert total == limit + 1

