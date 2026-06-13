import configparser
import json

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.core.memory import build_memory_guard_resume_context
from gear_optimizer.data.database import (
    get_db_connection,
    get_song_names_present_in_db,
    get_song_names_with_persisted_loadouts,
)


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


def test_get_song_names_present_in_db_require_loadouts_ignores_stub_songs_row():
    song_stub = "Stub Songs Row Only (Hard)"
    song_with_loadouts = "Has Loadouts (Hard)"

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            (song_stub, 0, 0, 0.0),
        )
        conn.execute(
            "INSERT OR REPLACE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            (song_with_loadouts, 456, 0, 0.0),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO team_buff_loadouts
            (song_name, team_buff, loadout_hash, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, timestamp)
            VALUES (?, 'T5', 'hash1', 456, 0, X'', X'', '{}', 0.0)
            """,
            (song_with_loadouts,),
        )
        conn.commit()
    finally:
        conn.close()

    present = get_song_names_with_persisted_loadouts([song_stub, song_with_loadouts])
    assert present == {song_with_loadouts}


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


def test_build_song_queue_resume_prepends_stub_db_songs_without_loadouts(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)

    song_resume = "Resume Song (Hard)"
    song_stub = "New Stub Song (Hard)"

    resume_fp = hard_dir / "resume.txt"
    stub_fp = hard_dir / "stub.txt"
    _write_song_stub(resume_fp, song_resume)
    _write_song_stub(stub_fp, song_stub)

    db_path = tmp_path / "resume_stub.db"
    resume_file = tmp_path / "memory_guard_resume.json"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setenv("METAFINDER_BIN_DIR", str(tmp_path / "bin"))

    conn = get_db_connection(str(db_path))
    try:
        conn.execute(
            "INSERT OR REPLACE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            (song_stub, 0, 0, 0.0),
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
    cfg.set("IterationEngine", "IgnoreResumeQueue", "false")

    resume_context = build_memory_guard_resume_context("hard", "", True, set(), True, set())
    resume_file.parent.mkdir(parents=True, exist_ok=True)
    resume_file.write_text(
        json.dumps(
            {
                "context": resume_context,
                "pending": [
                    {
                        "path": str(resume_fp.resolve()),
                        "song": song_resume,
                        "diff": "Hard",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("gear_optimizer.core.memory.MEMORY_GUARD_RESUME_FILE", str(resume_file))
    monkeypatch.setattr("gear_optimizer.app.MEMORY_GUARD_RESUME_FILE", str(resume_file))

    app = GearOptimizerApp()
    queue = app._build_song_queue(cfg, {"Hard": str(hard_dir)})

    assert [item[1] for item in queue] == [song_stub, song_resume]
