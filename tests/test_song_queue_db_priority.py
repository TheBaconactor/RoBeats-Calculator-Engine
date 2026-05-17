import configparser

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.data.database import get_db_connection, get_song_names_present_in_db


def _write_song_stub(path, song_name: str):
    path.write_text(
        "\n".join(
            [
                f"Song Name\t{song_name}",
                "Primary Color\tFlow",
                "Secondary Color\tBeat",
                "Difficulty\tHard",
                "Song Data",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_get_song_names_present_in_db_returns_only_existing_rows():
    song_in_db = "Already In DB (Hard)"
    song_missing = "Not In DB Yet (Hard)"

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            (song_in_db, 123, 0, 0.0),
        )
        conn.commit()
    finally:
        conn.close()

    present = get_song_names_present_in_db([song_in_db, song_missing])
    assert present == {song_in_db}


def test_build_song_queue_limit_preserves_missing_first(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)

    song_existing = "AAA Existing Song (Hard)"
    song_missing_a = "MMM Missing Song (Hard)"
    song_missing_b = "ZZZ Missing Song (Hard)"

    _write_song_stub(hard_dir / "existing.txt", song_existing)
    _write_song_stub(hard_dir / "missing_a.txt", song_missing_a)
    _write_song_stub(hard_dir / "missing_b.txt", song_missing_b)

    db_path = tmp_path / "priority_limit.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    conn = get_db_connection(str(db_path))
    try:
        conn.execute(
            "INSERT OR REPLACE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            (song_existing, 321, 0, 0.0),
        )
        conn.commit()
    finally:
        conn.close()

    cfg = configparser.ConfigParser()
    cfg.add_section("CalculateSong")
    cfg.set("CalculateSong", "Difficulty", "Hard")
    cfg.set("CalculateSong", "Song_Name", "")
    cfg.set("CalculateSong", "TargetPrimary", "all")
    cfg.set("CalculateSong", "TargetSecondary", "all")

    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "IgnoreResumeQueue", "true")
    cfg.set("IterationEngine", "SongQueueLimit", "2")

    app = GearOptimizerApp()
    queue = app._build_song_queue(cfg, {"Hard": str(hard_dir)})

    assert [item[1] for item in queue] == [song_missing_a, song_missing_b]
