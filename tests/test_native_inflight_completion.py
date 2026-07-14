from concurrent.futures import Future
import inspect

from gear_optimizer.solver.native_inflight_orchestrator import (
    CompletionTracker,
    emit_deferred_post_payload,
    finish_deferred_fg_completion,
    has_waitable_work,
    mark_song_completed,
    run_native_inflight_song_pipeline,
)
from tests.native_song_factory import make_native_song


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
    assert memory.completed == [("", "Song C")]
    assert bundle_callbacks == [("song-c", {"song-c"})]
    assert progress.done == [("progress-cb", "song-c")]


def test_emit_deferred_post_payload_defers_completion_when_fg_is_pending():
    song = make_native_song(song_name="Song FG", task_key="song-fg", fg_variants=None)
    completed = set()
    posted = []

    emitted = emit_deferred_post_payload(
        song,
        post=posted.append,
        completed_songs=completed,
        advance_bundle=lambda *_args, **_kwargs: None,
    )

    assert emitted is True
    assert len(posted) == 1
    assert posted[0]["_pending_fg_job"] is True
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
                "failed": False,
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
    assert memory.completed == [("", "Song Drain FG")]
    assert progress.done == [("progress-cb", "song-drain-fg")]


def test_finish_deferred_fg_completion_noops_when_no_completion_is_pending():
    song = make_native_song(song_name="Song Idle", task_key="song-idle")

    finished = finish_deferred_fg_completion(
        song,
        completed_songs=set(),
        advance_bundle=lambda *_args, **_kwargs: None,
    )

    assert finished is False


def test_native_inflight_fg_worker_failure_fails_loudly_instead_of_persisting_zero_fg():
    src = inspect.getsource(run_native_inflight_song_pipeline)

    assert "raise RuntimeError(f\"FG worker failed for {fg_song.config.task_key}\") from exc" in src
    assert "post_sender.send(build_failed_fg_update_payload(fg_song))" not in src


def test_decode_handoff_starts_fg_prep_before_fg_worker_submission():
    src = inspect.getsource(run_native_inflight_song_pipeline)

    queue_idx = src.index("fg_pipeline.queue(song")
    prep_idx = src.index("started_fg_prep = fg_pipeline.start_pending_prep", queue_idx)
    submit_idx = src.index("_submit_fg_jobs(", queue_idx)

    assert queue_idx < prep_idx < submit_idx
    assert "max_new=1" in src[prep_idx:submit_idx]


def test_fg_prep_failure_uses_bundle_aware_error_and_resolves_owner():
    src = inspect.getsource(run_native_inflight_song_pipeline)

    prep_error_idx = src.index("if prep_completion.error is None:")
    prep_error_block = src[prep_error_idx : src.index("if ready_fg_from_prep", prep_error_idx)]

    assert "build_native_song_error_payload(" in prep_error_block
    assert "build_native_task_error_payload(" not in prep_error_block
    assert "_advance_bundle(bundle_parent" in prep_error_block
    assert "mark_song_completed(" in prep_error_block
    # The slot was already released at GA completion; FG-stage errors must not
    # touch the slot pool.
    assert "release_slot" not in prep_error_block


def test_song_prep_runway_fill_is_not_gated_by_ga_admission():
    src = inspect.getsource(run_native_inflight_song_pipeline)

    first_fill_idx = src.index("if _fill_song_prep_runway():")
    backlog_gate_idx = src.index("if ga_should_pause_for_fg_backlog(")
    inner_fill_idx = src.index("if _fill_song_prep_runway():", backlog_gate_idx)

    assert first_fill_idx < backlog_gate_idx < inner_fill_idx
    assert "pending_tasks and (len(prepared) + len(prep_inflight) < icfg.prep_limit)" not in src


def test_song_prep_runway_fill_error_posts_task_payload_and_advances():
    """Replacement for the deleted synchronous-prime coverage (test_native_inflight_prime.py):
    the async runway fill absorbed the first-wave prep the old prime loop did serially. When a
    prep submit raises, _fill_song_prep_runway must post a task error payload and then either
    advance the repeat bundle or mark the song completed -- it must not swallow the failure or
    leave the task un-accounted. Pins the error branch the prime loop used to own."""
    src = inspect.getsource(run_native_inflight_song_pipeline)

    fill_idx = src.index("def _fill_song_prep_runway()")
    fill_block = src[fill_idx : src.index("def _emit_deferred_post_payload", fill_idx)]

    # A prep submit is attempted for the next queued task...
    assert "prep_queue.submit(" in fill_block
    # ...and a raised submit fails loud into the shared error/advance machinery (no swallow).
    assert "except Exception as exc:" in fill_block
    assert "build_native_task_error_payload(" in fill_block
    assert "_post(payload)" in fill_block
    assert "_advance_bundle(" in fill_block
    assert "mark_song_completed(" in fill_block


def test_song_prep_failures_do_not_treat_seed_context_as_repeat_bundle():
    src = inspect.getsource(run_native_inflight_song_pipeline)

    fill_idx = src.index("def _fill_song_prep_runway()")
    fill_block = src[fill_idx : src.index("def _emit_deferred_post_payload", fill_idx)]
    song_prep_idx = src.index("for prep_completion in prep_queue.pop_completed():")
    prep_error_block = src[song_prep_idx : src.index("ready_fg_from_prep = False", song_prep_idx)]

    assert "is_repeat_bundle = bool(bundle_tracker.bundle_runs(nxt))" in fill_block
    assert "suppress_progress=is_repeat_bundle" in fill_block
    assert "advanced = False" in fill_block
    assert "if not advanced:" in fill_block

    assert "is_repeat_bundle = bool(bundle_tracker.bundle_runs(task))" in prep_error_block
    assert "suppress_progress=is_repeat_bundle" in prep_error_block
    assert "advanced = False" in prep_error_block
    assert "if not advanced:" in prep_error_block
    assert "suppress_progress=repeat_ctx is not None" not in prep_error_block
    assert "if repeat_ctx is not None:" not in prep_error_block


def test_ga_admission_reserves_slot_fail_loud_before_payload_submit():
    src = inspect.getsource(run_native_inflight_song_pipeline)

    can_submit_idx = src.index("if can_submit_ga:")
    reserve_idx = src.index("ga_pipeline.reserve_slot(song, slot_pool)", can_submit_idx)
    payload_idx = src.index("payload = ga_pipeline.build_payload(song)", can_submit_idx)

    # Admission implies a free slot (queue limit <= usable slots): the reserve is
    # unguarded so NoFreeSongSlotError raises loudly, and there is no slot-warm
    # side channel left in the conveyor.
    assert reserve_idx < payload_idx
    assert "slot_warm" not in src
    assert "try:" not in src[can_submit_idx:reserve_idx]


def test_ga_completion_releases_slot_before_decode_handoff():
    src = inspect.getsource(run_native_inflight_song_pipeline)

    ga_done_idx = src.index("song.runtime.ga.ga_future = None")
    release_idx = src.index("ga_pipeline.release_slot(song, slot_pool)", ga_done_idx)
    decode_idx = src.index("decode_queue.submit(", ga_done_idx)

    # The GA request (GA loop + fused FG owner score + payload download) is the
    # only device consumer of the slot; it returns to the conveyor before any
    # host-side stage starts.
    assert release_idx < decode_idx
    assert "keep_slot_for_fg" not in src
    assert "fg_hold" not in src
