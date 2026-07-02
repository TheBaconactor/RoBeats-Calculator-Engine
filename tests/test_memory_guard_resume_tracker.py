from pathlib import Path

import gear_optimizer.core.memory as memory


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
