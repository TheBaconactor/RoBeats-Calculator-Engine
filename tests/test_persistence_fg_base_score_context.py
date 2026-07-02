import sqlite3
from pathlib import Path


def test_save_loadouts_batch_preserves_fg_base_score_context(monkeypatch, tmp_path: Path):
    """
    Regression: A single persistence entry can carry:
    - best base score (for team_buff_loadouts), and
    - a best-FG payload whose *paired base score* can be lower.

    We preserve the paired base score as `fg_base_score` so:
    - team_buff_fg_loadouts.score reflects the FG base context, and
    - songs.best_fg_score updates when fg_score > fg_base_score even if fg_score <= best base.
    """
    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    import gear_optimizer.data.database as db

    # Keep Stats recompute lightweight/deterministic (empty item pools are fine for this test).
    monkeypatch.setattr(db, "get_minis_by_name_cached", lambda: {})
    monkeypatch.setattr(db, "get_gears_by_name_cached", lambda: {})

    db.init_db()

    entry = {
        "score": 100,  # best base
        "fg_score": 95,  # FG improves vs its paired base, but not vs best base
        "fg_base_score": 90,  # paired base for the FG payload
        "gear": [],
        "minis": [],
        "details": {
            "Stats": {"Perfect Points": 0},
            "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "FT": 0,
            "FF": 0,
            "SelectedElement": "Beat",
            "PrimaryColor": "Beat",
            "SecondaryColor": "Chill",
        },
        "force": {
            "ForceGreats": {"final_score": 95},
            "details": {
                "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
                "FT": 0,
                "FF": 0,
                "SelectedElement": "Beat",
                "Stats": {"Perfect Points": 0},
            },
        },
    }

    db.save_loadouts_batch("pytest_song", [entry])

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        base_row = con.execute(
            "SELECT score, fg_score FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5' LIMIT 1",
            ("pytest_song",),
        ).fetchone()
        assert base_row is not None
        assert int(base_row["score"] or 0) == 100
        assert int(base_row["fg_score"] or 0) == 95

        fg_row = con.execute(
            "SELECT score, fg_score FROM team_buff_fg_loadouts WHERE song_name=? AND team_buff='T5' LIMIT 1",
            ("pytest_song",),
        ).fetchone()
        assert fg_row is not None
        assert int(fg_row["score"] or 0) == 90
        assert int(fg_row["fg_score"] or 0) == 95

        songs_row = con.execute("SELECT best_score, best_fg_score FROM songs WHERE name=? LIMIT 1", ("pytest_song",)).fetchone()
        assert songs_row is not None
        assert int(songs_row["best_score"] or 0) == 100
        assert int(songs_row["best_fg_score"] or 0) == 95
    finally:
        con.close()


def test_authoritative_fg_preserves_source_paired_base_score(monkeypatch):
    from gear_optimizer.helpers.song_helpers import persistence_authority as authority

    monkeypatch.setattr(
        authority,
        "score_stats_exact_with_timeline_trace",
        lambda *_args, **_kwargs: {"score": 160, "TimelineFrontier": {}},
    )
    monkeypatch.setattr(
        authority,
        "score_force_greats_response_surface_exact",
        lambda *_args, **_kwargs: 150,
    )

    entry = {
        "score": 160,
        "fg_score": 1,
        "fg_base_score": 100,
        "details": {"Stats": {"Perfect Points": 0}},
        "force": {
            "BaseScore": 100,
            "Score": 1,
            "Stats": {"Perfect Points": 0},
            "ForceGreats": {"config": {"NonFever1": 1}, "final_score": 1},
            "response_surface": [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        },
    }

    out = authority.canonicalize_authoritative_fg_entry(entry, calc_song={}, ref_arrays={})

    assert out["score"] == 160
    assert out["fg_base_score"] == 100
    assert out["fg_score"] == 150
    assert out["force"]["BaseScore"] == 100
    assert out["force"]["Score"] == 150
