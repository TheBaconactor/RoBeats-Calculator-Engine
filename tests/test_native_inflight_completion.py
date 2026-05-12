from concurrent.futures import Future

from gear_optimizer.solver.native_inflight_completion import CompletionTracker, has_waitable_work, mark_song_completed
from gear_optimizer.solver.native_inflight_types import make_native_song


def test_completion_tracker_registers_and_waits_for_future_completion():
    tracker = CompletionTracker()
    fut = Future()

    assert tracker.register(fut) is True
    assert tracker.register(fut) is False
    assert tracker.is_set() is False

    fut.set_result("done")

    assert tracker.wait(0.1, short_spin_s=0.0) is True
    assert tracker.is_set() is True

    tracker.clear()
    assert tracker.is_set() is False


def test_completion_tracker_unregister_discards_future_id():
    tracker = CompletionTracker()
    fut = Future()

    assert tracker.register(fut) is True

    tracker.unregister(id(fut))

    assert id(fut) not in tracker.ids


def test_has_waitable_work_detects_active_runtime_queues():
    assert has_waitable_work([], (), pending_fg=[]) is False
    assert has_waitable_work(["ga-song"], (), pending_fg=[]) is True


def test_has_waitable_work_detects_pending_fg_db_prefetch_future():
    song = make_native_song(task_key="fg-song", song_name="FG Song")
    song.runtime.db.db_loadouts_future = Future()

    assert has_waitable_work([], pending_fg=[song]) is True


class _MemoryResumeTracker:
    def __init__(self):
        self.completed = []

    def mark_completed(self, song_name):
        self.completed.append(song_name)


def test_mark_song_completed_updates_set_resume_tracker_and_callback():
    completed = set()
    memory = _MemoryResumeTracker()
    callbacks = []

    mark_song_completed(
        completed_songs=completed,
        task_key="song-a",
        song_name="Song A",
        memory_resume_tracker=memory,
        bundle_completed_cb=lambda key, done: callbacks.append((key, set(done))),
    )

    assert completed == {"song-a"}
    assert memory.completed == ["Song A"]
    assert callbacks == [("song-a", {"song-a"})]


def test_mark_song_completed_without_callback_preserves_failure_branch_behavior():
    completed = set()
    memory = _MemoryResumeTracker()

    mark_song_completed(
        completed_songs=completed,
        task_key="song-b",
        song_name="Song B",
        memory_resume_tracker=memory,
    )

    assert completed == {"song-b"}
    assert memory.completed == ["Song B"]
