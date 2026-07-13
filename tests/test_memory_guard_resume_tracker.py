import json
import logging
from pathlib import Path

import pytest

import gear_optimizer.core.memory as memory


def _queue_with_files(tmp_path, *song_names):
    queue = []
    for index, song_name in enumerate(song_names):
        song_path = tmp_path / f"song_{index}.txt"
        song_path.write_text("", encoding="utf-8")
        queue.append((str(song_path), song_name, "Hard"))
    return queue


def _install_resume_path(monkeypatch, resume_path):
    monkeypatch.setattr(memory, "MEMORY_GUARD_RESUME_FILE", str(resume_path))


def test_resume_tracker_replace_errors_do_not_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(memory.time, "sleep", lambda *_a, **_k: None)

    for exc in (PermissionError("denied"), FileNotFoundError("missing")):

        def _raise(*_a, _exc=exc, **_k):
            raise _exc

        monkeypatch.setattr(memory.os, "replace", _raise)

        resume_path = tmp_path / "resume.json"
        tracker = memory.MemoryGuardResumeTracker(str(resume_path))
        queue = [
            (str(tmp_path / "song1.txt"), "Song1", "Hard"),
            (str(tmp_path / "song2.txt"), "Song2", "Hard"),
        ]
        tracker.prime(queue, {"ctx": "x"})
        tracker.mark_completed(song_path=str(tmp_path / "song1.txt"))

        assert [entry["song"] for entry in tracker.pending] == ["Song2"]
        assert not list(tmp_path.glob("resume.json.*.tmp"))


def test_resume_tracker_mark_completed_prefers_path_over_name(tmp_path):
    resume_path = tmp_path / "resume.json"
    tracker = memory.MemoryGuardResumeTracker(str(resume_path))
    queue = [
        (str(tmp_path / "alpha.txt"), "Shared Name", "Hard"),
        (str(tmp_path / "beta.txt"), "Shared Name", "Hard"),
    ]
    tracker.prime(queue, {"ctx": "x"})
    tracker.mark_completed(song_path=str(tmp_path / "beta.txt"), song_name="Shared Name")

    assert [entry["path"] for entry in tracker.pending] == [str(tmp_path / "alpha.txt")]


def test_resume_tracker_persists_original_known_paths(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.json"
    monkeypatch.setattr(memory, "MEMORY_GUARD_RESUME_FILE", str(resume_path))
    tracker = memory.MemoryGuardResumeTracker(str(resume_path))
    queue = [
        (str(tmp_path / "alpha.txt"), "Alpha", "Hard"),
        (str(tmp_path / "beta.txt"), "Beta", "Hard"),
    ]
    for fp, _name, _diff in queue:
        Path(fp).write_text("", encoding="utf-8")
    tracker.prime(queue, {"ctx": "x"})
    assert tracker.pending_count() == 2
    tracker.mark_completed(song_path=str(tmp_path / "alpha.txt"))
    assert tracker.pending_count() == 1

    state = memory.load_memory_guard_resume_state()

    assert [item[1] for item in state.pending] == ["Beta"]
    assert state.known_path_keys == {
        memory.queue_path_key((queue[0][0], "", "")),
        memory.queue_path_key((queue[1][0], "", "")),
    }


def test_resume_tracker_journal_recovery_preserves_pending_order(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.json"
    _install_resume_path(monkeypatch, resume_path)
    queue = _queue_with_files(tmp_path, "Alpha", "Beta", "Gamma")
    tracker = memory.MemoryGuardResumeTracker(str(resume_path))
    tracker.prime(queue, {"ctx": "x"})

    tracker.mark_completed(song_path=queue[1][0])

    snapshot = json.loads(resume_path.read_text(encoding="utf-8"))
    assert [entry["song"] for entry in snapshot["pending"]] == ["Alpha", "Beta", "Gamma"]
    state = memory.load_memory_guard_resume_state({"ctx": "x"})
    assert [item[1] for item in state.pending] == ["Alpha", "Gamma"]


def test_resume_tracker_duplicate_completion_appends_one_record(tmp_path):
    resume_path = tmp_path / "resume.json"
    queue = _queue_with_files(tmp_path, "Alpha", "Beta", "Gamma")
    tracker = memory.MemoryGuardResumeTracker(str(resume_path))
    tracker.prime(queue, {"ctx": "x"})

    tracker.mark_completed(song_path=queue[1][0])
    tracker.mark_completed(song_path=queue[1][0])

    journal_path = Path(memory._memory_guard_resume_journal_path(str(resume_path)))
    assert len(journal_path.read_text(encoding="utf-8").splitlines()) == 1
    assert [entry["song"] for entry in tracker.pending] == ["Alpha", "Gamma"]


def test_resume_tracker_name_fallback_completes_duplicate_names_in_order(tmp_path):
    resume_path = tmp_path / "resume.json"
    queue = _queue_with_files(tmp_path, "Shared", "Other", "Shared")
    tracker = memory.MemoryGuardResumeTracker(str(resume_path))
    tracker.prime(queue, {"ctx": "x"})

    tracker.mark_completed(song_name=" shared ")
    assert [entry["path"] for entry in tracker.pending] == [queue[1][0], queue[2][0]]
    tracker.mark_completed(song_name="SHARED")
    assert [entry["path"] for entry in tracker.pending] == [queue[1][0]]


def test_resume_tracker_ignores_torn_journal_tail_after_valid_records(tmp_path, monkeypatch, caplog):
    resume_path = tmp_path / "resume.json"
    _install_resume_path(monkeypatch, resume_path)
    queue = _queue_with_files(tmp_path, "Alpha", "Beta", "Gamma")
    tracker = memory.MemoryGuardResumeTracker(str(resume_path))
    tracker.prime(queue, {"ctx": "x"})
    tracker.mark_completed(song_path=queue[0][0])
    journal_path = Path(memory._memory_guard_resume_journal_path(str(resume_path)))
    with journal_path.open("a", encoding="utf-8") as fh:
        fh.write('{"generation":')

    with caplog.at_level(logging.WARNING):
        state = memory.load_memory_guard_resume_state({"ctx": "x"})

    assert [item[1] for item in state.pending] == ["Beta", "Gamma"]
    assert "Ignoring torn resume journal tail" in caplog.text

    restarted = memory.MemoryGuardResumeTracker(str(resume_path))
    restarted.prime(state.pending, {"ctx": "x"})
    restarted.mark_completed(song_path=queue[1][0])
    assert [item[1] for item in memory.load_memory_guard_resume_state({"ctx": "x"}).pending] == ["Gamma"]


def test_resume_tracker_context_mismatch_ignores_snapshot_and_journal(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.json"
    _install_resume_path(monkeypatch, resume_path)
    queue = _queue_with_files(tmp_path, "Alpha", "Beta")
    tracker = memory.MemoryGuardResumeTracker(str(resume_path))
    tracker.prime(queue, {"ctx": "original"})
    tracker.mark_completed(song_path=queue[0][0])

    state = memory.load_memory_guard_resume_state({"ctx": "different"})

    assert state.pending == []
    assert state.known_path_keys is None


def test_resume_tracker_compaction_is_generation_safe(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.json"
    _install_resume_path(monkeypatch, resume_path)
    queue = _queue_with_files(tmp_path, "Alpha", "Beta", "Gamma", "Delta")
    tracker = memory.MemoryGuardResumeTracker(str(resume_path))
    tracker._MIN_COMPACTION_COMPLETIONS = 1
    tracker.prime(queue, {"ctx": "x"})
    old_generation = tracker._generation
    tracker.mark_completed(song_path=queue[0][0])
    tracker.mark_completed(song_path=queue[1][0])

    compacted_snapshot = json.loads(resume_path.read_text(encoding="utf-8"))
    assert compacted_snapshot["generation"] != old_generation
    assert compacted_snapshot["journal_compacted"] is True
    assert [entry["song"] for entry in compacted_snapshot["pending"]] == ["Gamma", "Delta"]

    journal_path = Path(memory._memory_guard_resume_journal_path(str(resume_path)))
    stale_record = {"generation": old_generation, "path": queue[3][0]}
    journal_path.write_text(json.dumps(stale_record) + "\n", encoding="utf-8")
    tracker.mark_completed(song_path=queue[2][0])

    state = memory.load_memory_guard_resume_state({"ctx": "x"})
    assert [item[1] for item in state.pending] == ["Delta"]


def test_resume_tracker_restart_reuses_journal_and_original_known_paths(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.json"
    _install_resume_path(monkeypatch, resume_path)
    queue = _queue_with_files(tmp_path, "Alpha", "Beta", "Gamma")
    first = memory.MemoryGuardResumeTracker(str(resume_path))
    first.prime(queue, {"ctx": "x"})
    first.mark_completed(song_path=queue[0][0])

    second = memory.MemoryGuardResumeTracker(str(resume_path))
    second.prime(queue[1:], {"ctx": "x"})

    assert second._generation == first._generation
    assert second.known_paths == [item[0] for item in queue]
    second.mark_completed(song_path=queue[1][0])
    state = memory.load_memory_guard_resume_state({"ctx": "x"})
    assert [item[1] for item in state.pending] == ["Gamma"]


def test_resume_tracker_append_failure_falls_back_to_atomic_snapshot(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.json"
    _install_resume_path(monkeypatch, resume_path)
    queue = _queue_with_files(tmp_path, "Alpha", "Beta")
    tracker = memory.MemoryGuardResumeTracker(str(resume_path))
    tracker.prime(queue, {"ctx": "x"})
    monkeypatch.setattr(tracker, "_append_completion_locked", lambda _path: False)

    tracker.mark_completed(song_path=queue[0][0])

    state = memory.load_memory_guard_resume_state({"ctx": "x"})
    assert [item[1] for item in state.pending] == ["Beta"]


def test_resume_tracker_rejects_duplicate_queue_paths(tmp_path):
    resume_path = tmp_path / "resume.json"
    queue = _queue_with_files(tmp_path, "Alpha")
    duplicate_path_queue = [queue[0], (queue[0][0], "Different Name", "Hard")]
    tracker = memory.MemoryGuardResumeTracker(str(resume_path))

    with pytest.raises(ValueError, match="Duplicate path"):
        tracker.prime(duplicate_path_queue, {"ctx": "x"})


def test_resume_tracker_full_completion_removes_snapshot_and_journal(tmp_path, monkeypatch):
    resume_path = tmp_path / "resume.json"
    _install_resume_path(monkeypatch, resume_path)
    queue = _queue_with_files(tmp_path, "Alpha", "Beta")
    tracker = memory.MemoryGuardResumeTracker(str(resume_path))
    tracker.prime(queue, {"ctx": "x"})

    tracker.mark_completed(song_path=queue[0][0])
    tracker.mark_completed(song_path=queue[1][0])

    assert not resume_path.exists()
    assert not Path(memory._memory_guard_resume_journal_path(str(resume_path))).exists()
    assert memory.load_memory_guard_resume_state({"ctx": "x"}).pending == []
