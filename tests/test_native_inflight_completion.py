from concurrent.futures import Future

from gear_optimizer.solver.native_inflight_completion import (
    CompletionTracker,
    emit_deferred_post_payload,
    finish_deferred_fg_completion,
    has_waitable_work,
    mark_song_completed,
)
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


class _ProgressTracker:
    def __init__(self):
        self.done = []

    def emit_done_song_progress(self, progress_cb, song):
        self.done.append((progress_cb, song.config.task_key))


def test_emit_deferred_post_payload_posts_once_and_marks_fg_scored_song_completed():
    song = make_native_song(song_name="Song C", task_key="song-c", fg_variants=[])
    completed = set()
    memory = _MemoryResumeTracker()
    progress = _ProgressTracker()
    posted = []
    bundle_callbacks = []

    emitted = emit_deferred_post_payload(
        song,
        post=posted.append,
        persist_pending_fg_job=True,
        completed_songs=completed,
        memory_resume_tracker=memory,
        bundle_completed_cb=lambda key, done: bundle_callbacks.append((key, set(done))),
        advance_bundle=lambda *_args, **_kwargs: None,
        progress_tracker=progress,
        progress_cb="progress-cb",
    )
    emitted_again = emit_deferred_post_payload(
        song,
        post=posted.append,
        persist_pending_fg_job=True,
        completed_songs=completed,
        memory_resume_tracker=memory,
        bundle_completed_cb=None,
        advance_bundle=lambda *_args, **_kwargs: None,
        progress_tracker=progress,
        progress_cb="progress-cb",
    )

    assert emitted is True
    assert emitted_again is False
    assert len(posted) == 1
    assert posted[0]["_deferred_post"] is True
    assert song.runtime.post.deferred_post_emitted is True
    assert completed == {"song-c"}
    assert memory.completed == ["Song C"]
    assert bundle_callbacks == [("song-c", {"song-c"})]
    assert progress.done == [("progress-cb", "song-c")]


def test_emit_deferred_post_payload_defers_completion_when_fg_is_pending():
    song = make_native_song(song_name="Song FG", task_key="song-fg", fg_variants=None)
    completed = set()
    posted = []

    emitted = emit_deferred_post_payload(
        song,
        post=posted.append,
        persist_pending_fg_job=False,
        completed_songs=completed,
        advance_bundle=lambda *_args, **_kwargs: None,
    )

    assert emitted is True
    assert len(posted) == 1
    assert posted[0]["_pending_fg_job"] is True
    assert posted[0]["_persist_pending_fg_job"] is False
    assert song.runtime.post.await_fg_completion_progress is True
    assert completed == set()


def test_finish_deferred_fg_completion_advances_waiting_bundle():
    parent = object()
    song = make_native_song(song_name="Song Bundle FG", task_key="song-bundle-fg")
    song.runtime.bundle.bundle_parent_task = parent
    song.runtime.bundle.bundle_wait_for_fg = True
    song.runtime.db.record_info = {"improved": True}
    advanced = []

    finished = finish_deferred_fg_completion(
        song,
        fg_failed=True,
        completed_songs=set(),
        advance_bundle=lambda *args, **kwargs: advanced.append((args, kwargs)),
    )

    assert finished is True
    assert song.runtime.bundle.bundle_wait_for_fg is False
    assert advanced == [
        (
            (parent,),
            {
                "song_name": "Song Bundle FG",
                "record_info": {"improved": True},
                "failed": True,
            },
        )
    ]


def test_finish_deferred_fg_completion_marks_drain_at_end_song_done():
    song = make_native_song(song_name="Song Drain FG", task_key="song-drain-fg")
    song.runtime.post.await_fg_completion_progress = True
    completed = set()
    memory = _MemoryResumeTracker()
    progress = _ProgressTracker()

    finished = finish_deferred_fg_completion(
        song,
        fg_failed=False,
        completed_songs=completed,
        memory_resume_tracker=memory,
        bundle_completed_cb=None,
        advance_bundle=lambda *_args, **_kwargs: None,
        progress_tracker=progress,
        progress_cb="progress-cb",
    )

    assert finished is True
    assert song.runtime.post.await_fg_completion_progress is False
    assert completed == {"song-drain-fg"}
    assert memory.completed == ["Song Drain FG"]
    assert progress.done == [("progress-cb", "song-drain-fg")]


def test_finish_deferred_fg_completion_noops_when_no_completion_is_pending():
    song = make_native_song(song_name="Song Idle", task_key="song-idle")

    finished = finish_deferred_fg_completion(
        song,
        fg_failed=False,
        completed_songs=set(),
        advance_bundle=lambda *_args, **_kwargs: None,
    )

    assert finished is False
