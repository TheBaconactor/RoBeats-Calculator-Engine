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
        tracker.mark_completed("Song1")

        assert [entry["song"] for entry in tracker.pending] == ["Song2"]
        assert not (tmp_path / "resume.json.tmp").exists()
