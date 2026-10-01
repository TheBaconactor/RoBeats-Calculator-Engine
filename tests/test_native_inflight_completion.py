from concurrent.futures import Future
import inspect

from gear_optimizer.solver import native_inflight_completion as completion
from gear_optimizer.solver.native_inflight_completion import mark_song_completed
from tests.native_song_factory import make_native_song


class _MemoryResumeTracker:
    def __init__(self):
        self.completed = []

    def mark_completed(self, *, song_path=None, song_name=None):
        self.completed.append((song_path, song_name))


def test_mark_song_completed_updates_set_resume_tracker_and_callback():
    completed = set()
    memory = _MemoryResumeTracker()
    callbacks = []

    mark_song_completed(
        completed_songs=completed,
        task_key="song-a",
        song_name="Song A",
        song_path="C:/songs/song-a.txt",
        memory_resume_tracker=memory,
        bundle_completed_cb=lambda key, done: callbacks.append((key, set(done))),
    )

    assert completed == {"song-a"}
    assert memory.completed == [("C:/songs/song-a.txt", "Song A")]
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
    assert memory.completed == [(None, "Song B")]


class _ProgressTracker:
    def __init__(self):
        self.done = []

    def emit_done_song_progress(self, progress_cb, song):
        self.done.append((progress_cb, song.config.task_key))


