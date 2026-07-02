import configparser
import json

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.core.memory import build_memory_guard_resume_context
from gear_optimizer.song_queue import finalize_song_queue, merge_discovered_with_resume, queue_path_key
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


def _make_hard_queue_cfg(*, ignore_resume: bool = False, song_queue_limit: int = 0) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.add_section("CalculateSong")
    cfg.set("CalculateSong", "Difficulty", "Hard")
    cfg.set("CalculateSong", "Song_Name", "")
    cfg.set("CalculateSong", "TargetPrimary", "all")
    cfg.set("CalculateSong", "TargetSecondary", "all")
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "IgnoreResumeQueue", "true" if ignore_resume else "false")
    if song_queue_limit > 0:
        cfg.set("IterationEngine", "SongQueueLimit", str(song_queue_limit))
    return cfg


def _install_resume_file(
    monkeypatch,
    tmp_path,
    *,
    resume_entries: list[dict],
    known_paths: list[str] | None = None,
):
    resume_context = build_memory_guard_resume_context("hard", "", True, set(), True, set())
    resume_file = tmp_path / "memory_guard_resume.json"
    resume_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"context": resume_context, "pending": resume_entries}
    if known_paths is not None:
        payload["known_paths"] = known_paths
    resume_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr("gear_optimizer.core.memory.MEMORY_GUARD_RESUME_FILE", str(resume_file))
    monkeypatch.setattr("gear_optimizer.app.MEMORY_GUARD_RESUME_FILE", str(resume_file))
    return resume_file


def _setup_resume_queue_env(monkeypatch, tmp_path, db_name: str):
    db_path = tmp_path / db_name
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setenv("METAFINDER_BIN_DIR", str(tmp_path / "bin"))
    return db_path


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

    cfg = _make_hard_queue_cfg(ignore_resume=True, song_queue_limit=2)

    app = GearOptimizerApp()
    queue = app._build_song_queue(cfg, {"Hard": str(hard_dir)})

    assert [item[1] for item in queue] == [song_missing_a, song_missing_b]


def test_merge_discovered_with_resume_prepends_by_path_only():
    resume = [("C:/resume.txt", "Resume Song", "Hard")]
    discovered = [
        ("C:/new.txt", "New Song", "Hard"),
        ("C:/resume.txt", "Resume Song", "Hard"),
    ]
    merged, prepended = merge_discovered_with_resume(
        discovered_queue=discovered,
        resume_queue=resume,
    )
    assert prepended == 1
    assert [item[1] for item in merged] == ["New Song", "Resume Song"]


def test_merge_discovered_with_resume_does_not_readd_completed_known_path():
    completed = ("C:/completed.txt", "Completed Song", "Hard")
    resume = [("C:/resume.txt", "Resume Song", "Hard")]
    new = ("C:/new.txt", "New Song", "Hard")
    discovered = [completed, new, *resume]

    merged, prepended = merge_discovered_with_resume(
        discovered_queue=discovered,
        resume_queue=resume,
        resume_known_path_keys={queue_path_key(completed), queue_path_key(resume[0])},
    )

    assert prepended == 1
    assert [item[1] for item in merged] == ["New Song", "Resume Song"]


def test_merge_discovered_with_resume_path_key_is_case_insensitive():
    resume = [("C:/Resume.TXT", "Resume Song", "Hard")]
    discovered = [("c:/resume.txt", "Resume Song", "Hard")]
    merged, prepended = merge_discovered_with_resume(
        discovered_queue=discovered,
        resume_queue=resume,
    )
    assert prepended == 0
    assert len(merged) == 1


def test_finalize_song_queue_resume_limit_keeps_prepended_block():
    resume = [(f"C:/resume{i}.txt", f"Resume {i}", "Hard") for i in range(5)]
    discovered = [(f"C:/new{i}.txt", f"New {i}", "Hard") for i in range(3)] + resume
    result = finalize_song_queue(
        discovered_queue=discovered,
        resume_queue=resume,
        resume_known_path_keys={queue_path_key(item) for item in resume},
        song_queue_limit=4,
    )
    assert result.prepended_count == 3
    assert result.limit_applied is True
    assert len(result.queue) == 4
    assert [item[1] for item in result.queue[:3]] == ["New 0", "New 1", "New 2"]
    assert result.queue[3][1] == "Resume 0"


def test_build_song_queue_resume_prepends_new_path_even_with_loadouts(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)

    song_resume = "Resume Song (Hard)"
    song_new = "Imported With Loadouts (Hard)"

    resume_fp = hard_dir / "resume.txt"
    new_fp = hard_dir / "new.txt"
    _write_song_stub(resume_fp, song_resume)
    _write_song_stub(new_fp, song_new)

    _setup_resume_queue_env(monkeypatch, tmp_path, "resume_loadout.db")
    conn = get_db_connection(str(tmp_path / "resume_loadout.db"))
    try:
        conn.execute(
            "INSERT OR REPLACE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            (song_new, 999, 0, 0.0),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO team_buff_loadouts
            (song_name, team_buff, loadout_hash, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, timestamp)
            VALUES (?, 'T5', 'hash1', 999, 0, X'', X'', '{}', 0.0)
            """,
            (song_new,),
        )
        conn.commit()
    finally:
        conn.close()

    _install_resume_file(
        monkeypatch,
        tmp_path,
        resume_entries=[
            {"path": str(resume_fp.resolve()), "song": song_resume, "diff": "Hard"},
        ],
        known_paths=[str(resume_fp.resolve())],
    )

    app = GearOptimizerApp()
    queue = app._build_song_queue(_make_hard_queue_cfg(), {"Hard": str(hard_dir)})

    assert [item[1] for item in queue] == [song_new, song_resume]


def test_build_song_queue_resume_prepends_stub_db_songs_without_loadouts(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)

    song_resume = "Resume Song (Hard)"
    song_stub = "New Stub Song (Hard)"

    resume_fp = hard_dir / "resume.txt"
    stub_fp = hard_dir / "stub.txt"
    _write_song_stub(resume_fp, song_resume)
    _write_song_stub(stub_fp, song_stub)

    _setup_resume_queue_env(monkeypatch, tmp_path, "resume_stub.db")
    conn = get_db_connection(str(tmp_path / "resume_stub.db"))
    try:
        conn.execute(
            "INSERT OR REPLACE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, ?, ?, ?)",
            (song_stub, 0, 0, 0.0),
        )
        conn.commit()
    finally:
        conn.close()

    _install_resume_file(
        monkeypatch,
        tmp_path,
        resume_entries=[
            {"path": str(resume_fp.resolve()), "song": song_resume, "diff": "Hard"},
        ],
        known_paths=[str(resume_fp.resolve())],
    )

    app = GearOptimizerApp()
    queue = app._build_song_queue(_make_hard_queue_cfg(), {"Hard": str(hard_dir)})

    assert [item[1] for item in queue] == [song_stub, song_resume]


def test_build_song_queue_resume_limit_preserves_prepended_paths(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)

    song_resume_a = "Resume A (Hard)"
    song_resume_b = "Resume B (Hard)"
    song_new_a = "New A (Hard)"
    song_new_b = "New B (Hard)"

    resume_fp_a = hard_dir / "resume_a.txt"
    resume_fp_b = hard_dir / "resume_b.txt"
    new_fp_a = hard_dir / "new_a.txt"
    new_fp_b = hard_dir / "new_b.txt"
    for fp, name in (
        (resume_fp_a, song_resume_a),
        (resume_fp_b, song_resume_b),
        (new_fp_a, song_new_a),
        (new_fp_b, song_new_b),
    ):
        _write_song_stub(fp, name)

    _setup_resume_queue_env(monkeypatch, tmp_path, "resume_limit.db")
    _install_resume_file(
        monkeypatch,
        tmp_path,
        resume_entries=[
            {"path": str(resume_fp_a.resolve()), "song": song_resume_a, "diff": "Hard"},
            {"path": str(resume_fp_b.resolve()), "song": song_resume_b, "diff": "Hard"},
        ],
        known_paths=[str(resume_fp_a.resolve()), str(resume_fp_b.resolve())],
    )

    app = GearOptimizerApp()
    queue = app._build_song_queue(
        _make_hard_queue_cfg(song_queue_limit=3),
        {"Hard": str(hard_dir)},
    )

    assert [item[1] for item in queue] == [song_new_a, song_new_b, song_resume_a]
    assert queue_path_key(queue[0]) == queue_path_key((str(new_fp_a.resolve()), song_new_a, "Hard"))


def test_build_song_queue_legacy_resume_does_not_prepend_completed_paths(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)

    song_completed = "Completed Before Restart (Hard)"
    song_resume = "Still Pending (Hard)"

    completed_fp = hard_dir / "completed.txt"
    resume_fp = hard_dir / "resume.txt"
    _write_song_stub(completed_fp, song_completed)
    _write_song_stub(resume_fp, song_resume)

    _setup_resume_queue_env(monkeypatch, tmp_path, "legacy_resume.db")
    _install_resume_file(
        monkeypatch,
        tmp_path,
        resume_entries=[
            {"path": str(resume_fp.resolve()), "song": song_resume, "diff": "Hard"},
        ],
        known_paths=None,
    )

    app = GearOptimizerApp()
    queue = app._build_song_queue(_make_hard_queue_cfg(), {"Hard": str(hard_dir)})

    assert [item[1] for item in queue] == [song_resume]
