import json

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.settings import RunSettings
from gear_optimizer.core.memory import MemoryGuardResumeTracker, build_memory_guard_resume_context
from gear_optimizer.song_queue import finalize_song_queue, merge_discovered_with_resume, queue_path_key
from gear_optimizer.store import db, schema
from tests.store_support import result


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


def _hard_queue_run(*, ignore_resume: bool = False, song_queue_limit: int = 0) -> RunSettings:
    return RunSettings(difficulty="Hard", ignore_resume_queue=ignore_resume, song_queue_limit=song_queue_limit)


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
    return db_path


def _install_completed_resume_crash_window(monkeypatch, tmp_path, queue):
    resume_file = tmp_path / "memory_guard_resume.json"
    resume_context = build_memory_guard_resume_context("hard", "", True, set(), True, set())
    monkeypatch.setattr("gear_optimizer.core.memory.MEMORY_GUARD_RESUME_FILE", str(resume_file))
    tracker = MemoryGuardResumeTracker(str(resume_file))
    tracker.prime(queue, resume_context)
    monkeypatch.setattr(tracker, "_remove_state_locked", lambda: None)
    for song_path, song_name, _difficulty in queue:
        tracker.mark_completed(song_path=song_path, song_name=song_name)
    assert resume_file.exists()
    assert (tmp_path / "memory_guard_resume.json.completed.jsonl").exists()
    return resume_file


def test_present_songs_are_the_processed_ones(tmp_path):
    song_in_db = "Already In DB (Hard)"
    song_empty_run = "Processed Without Results (Hard)"
    _mark_processed(tmp_path / "presence.db", song_in_db, with_loadouts=True)
    _mark_processed(tmp_path / "presence.db", song_empty_run)
    conn = schema.connect(tmp_path / "presence.db")
    try:
        assert db.present_songs(conn, [song_in_db, song_empty_run, "Not In DB Yet (Hard)"]) == {song_in_db, song_empty_run}
    finally:
        conn.close()


def test_build_song_queue_limit_preserves_missing_first(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_DATA_DIR", str(tmp_path))

    song_existing = "AAA Existing Song (Hard)"
    song_missing_a = "MMM Missing Song (Hard)"
    song_missing_b = "ZZZ Missing Song (Hard)"

    _write_song_stub(hard_dir / "existing.txt", song_existing)
    _write_song_stub(hard_dir / "missing_a.txt", song_missing_a)
    _write_song_stub(hard_dir / "missing_b.txt", song_missing_b)

    db_path = tmp_path / "priority_limit.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))

    _mark_processed(db_path, song_existing)

    app = GearOptimizerApp()
    queue = app._build_song_queue(_hard_queue_run(ignore_resume=True, song_queue_limit=2))

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
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_DATA_DIR", str(tmp_path))

    song_resume = "Resume Song (Hard)"
    song_new = "Imported With Loadouts (Hard)"

    resume_fp = hard_dir / "resume.txt"
    new_fp = hard_dir / "new.txt"
    _write_song_stub(resume_fp, song_resume)
    _write_song_stub(new_fp, song_new)

    _setup_resume_queue_env(monkeypatch, tmp_path, "resume_loadout.db")
    _mark_processed(tmp_path / "resume_loadout.db", song_new, with_loadouts=True)

    _install_resume_file(
        monkeypatch,
        tmp_path,
        resume_entries=[
            {"path": str(resume_fp.resolve()), "song": song_resume, "diff": "Hard"},
        ],
        known_paths=[str(resume_fp.resolve())],
    )

    app = GearOptimizerApp()
    queue = app._build_song_queue(_hard_queue_run())

    assert [item[1] for item in queue] == [song_new, song_resume]


def test_build_song_queue_resume_prepends_stub_db_songs_without_loadouts(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_DATA_DIR", str(tmp_path))

    song_resume = "Resume Song (Hard)"
    song_stub = "New Stub Song (Hard)"

    resume_fp = hard_dir / "resume.txt"
    stub_fp = hard_dir / "stub.txt"
    _write_song_stub(resume_fp, song_resume)
    _write_song_stub(stub_fp, song_stub)

    _setup_resume_queue_env(monkeypatch, tmp_path, "resume_stub.db")
    _mark_processed(tmp_path / "resume_stub.db", song_stub)

    _install_resume_file(
        monkeypatch,
        tmp_path,
        resume_entries=[
            {"path": str(resume_fp.resolve()), "song": song_resume, "diff": "Hard"},
        ],
        known_paths=[str(resume_fp.resolve())],
    )

    app = GearOptimizerApp()
    queue = app._build_song_queue(_hard_queue_run())

    assert [item[1] for item in queue] == [song_stub, song_resume]


def test_build_song_queue_resume_limit_preserves_prepended_paths(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_DATA_DIR", str(tmp_path))

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
    queue = app._build_song_queue(_hard_queue_run(song_queue_limit=3))

    assert [item[1] for item in queue] == [song_new_a, song_new_b, song_resume_a]
    assert queue_path_key(queue[0]) == queue_path_key((str(new_fp_a.resolve()), song_new_a, "Hard"))


def test_build_song_queue_legacy_resume_does_not_prepend_completed_paths(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_DATA_DIR", str(tmp_path))

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
    queue = app._build_song_queue(_hard_queue_run())

    assert [item[1] for item in queue] == [song_resume]


def test_build_song_queue_completed_journal_crash_window_does_not_requeue_known_paths(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_DATA_DIR", str(tmp_path))
    completed_name = "Completed Before State Removal (Hard)"
    completed_path = hard_dir / "completed.txt"
    _write_song_stub(completed_path, completed_name)
    _setup_resume_queue_env(monkeypatch, tmp_path, "completed_crash_window.db")
    _install_completed_resume_crash_window(
        monkeypatch,
        tmp_path,
        [(str(completed_path), completed_name, "Hard")],
    )

    queue = GearOptimizerApp()._build_song_queue(_hard_queue_run())

    assert queue == []


def test_build_song_queue_completed_journal_crash_window_admits_new_path(monkeypatch, tmp_path):
    hard_dir = tmp_path / "Hard"
    hard_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_DATA_DIR", str(tmp_path))
    completed_name = "Completed Before Import (Hard)"
    new_name = "Imported After Snapshot (Hard)"
    completed_path = hard_dir / "completed.txt"
    new_path = hard_dir / "new.txt"
    _write_song_stub(completed_path, completed_name)
    _setup_resume_queue_env(monkeypatch, tmp_path, "completed_with_import.db")
    _install_completed_resume_crash_window(
        monkeypatch,
        tmp_path,
        [(str(completed_path), completed_name, "Hard")],
    )
    _write_song_stub(new_path, new_name)

    queue = GearOptimizerApp()._build_song_queue(_hard_queue_run())

    assert [item[1] for item in queue] == [new_name]


def _mark_processed(db_path, song: str, *, with_loadouts: bool = False) -> None:
    """The song as the results database records it after a run (with a stored result, or none)."""
    conn = schema.connect(db_path, write=True)
    try:
        db.store_results(conn, song, "T5", [result("h1", 999, song=song)] if with_loadouts else [])
    finally:
        conn.close()
