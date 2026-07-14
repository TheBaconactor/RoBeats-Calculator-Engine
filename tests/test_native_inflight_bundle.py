from collections import deque

from gear_optimizer.domain.jobs import task_file_path
from gear_optimizer.solver.native_inflight_lifecycle import InflightBundleTracker
from tests.native_song_factory import make_native_song


def _bundle_task():
    prefix = (
        "song.txt",
        "Bundle Song",
        "Hard",
        {},
        None,
        None,
        None,
        None,
        None,
        None,
        False,
        False,
        1,
        None,
        1,
        False,
    )
    bundle = {
        "repeat_bundle": True,
        "repeat_total": 2,
        "runs": [
            {"repeat_index": 1, "repeat_total": 2, "ga_seed": 101},
            {"repeat_index": 2, "repeat_total": 2, "ga_seed": 202},
        ],
    }
    return prefix + (bundle,)


class _MemoryResume:
    def __init__(self):
        self.completed: list[tuple[str | None, str | None]] = []

    def mark_completed(self, *, song_path=None, song_name=None):
        self.completed.append((song_path, song_name))


def test_bundle_tracker_materializes_and_binds_repeat_context():
    parent = _bundle_task()
    tracker = InflightBundleTracker(
        pending_tasks=deque(),
        completed_songs=set(),
        memory_resume_tracker=None,
        bundle_completed_cb=None,
        emit_progress=lambda **_kwargs: None,
    )

    logical_task, repeat_ctx = tracker.next_logical_task(parent)
    song = make_native_song(song_name="Bundle Song", task_key="Bundle Song")

    tracker.bind_song(song, parent, repeat_ctx)

    assert logical_task[:16] == parent[:16]
    assert logical_task[16] == {"repeat_index": 1, "repeat_total": 2, "ga_seed": 101}
    assert song.runtime.bundle.bundle_parent_task is parent
    assert song.runtime.bundle.bundle_task_key == "Bundle Song"
    assert song.runtime.bundle.bundle_repeat_index == 1
    assert song.runtime.bundle.bundle_repeat_total == 2


def test_bundle_tracker_advances_repeats_then_marks_parent_complete():
    parent = _bundle_task()
    pending = deque()
    completed: set[str] = set()
    memory_resume = _MemoryResume()
    callbacks: list[tuple[str, set[str]]] = []
    progress: list[dict] = []

    tracker = InflightBundleTracker(
        pending_tasks=pending,
        completed_songs=completed,
        memory_resume_tracker=memory_resume,
        bundle_completed_cb=lambda key, done: callbacks.append((str(key), set(done))),
        emit_progress=lambda **kwargs: progress.append(dict(kwargs)),
    )

    assert tracker.advance(parent, song_name="Bundle Song") is True
    assert list(pending) == [parent]
    assert completed == set()
    assert memory_resume.completed == []
    assert progress[-1] == {
        "completed_delta": 1,
        "failed_delta": 0,
        "record_info": {"song": "Bundle Song (Run 1/2)", "status": "DONE"},
    }

    assert tracker.advance(parent, song_name="Bundle Song", failed=True) is True
    assert completed == {"Bundle Song"}
    assert memory_resume.completed == [(task_file_path(parent), "Bundle Song")]
    assert callbacks == [("Bundle Song", {"Bundle Song"})]
    assert progress[-1] == {
        "completed_delta": 1,
        "failed_delta": 1,
        "record_info": {"song": "Bundle Song (Run 2/2)", "status": "FAILED"},
    }
