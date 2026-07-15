from __future__ import annotations

import threading
import time
from concurrent.futures import Future

import numpy as np
import pytest

from gear_optimizer.solver.native_inflight_pipeline import (
    InflightBasePipeline,
    NativeFGPipeline,
    NativeFGPipelineSettings,
    run_fg_job_sync,
    read_native_fg_pipeline_settings,
)
from tests.native_song_factory import make_native_song


def test_read_native_fg_pipeline_settings_uses_canonical_sizing():
    sizing_calls: list[dict[str, int | str]] = []

    def fg_prep_sizer(**kwargs):
        sizing_calls.append(dict(kwargs))
        return 6

    single_song_settings = read_native_fg_pipeline_settings(
        inflight_limit=1,
        default_worker_threads=fg_prep_sizer,
    )

    assert single_song_settings.workers == 1
    assert single_song_settings.batch_max == 1
    assert single_song_settings.prep_workers == 1
    assert single_song_settings.db_prefetch_workers == 1

    settings = read_native_fg_pipeline_settings(
        inflight_limit=8,
        default_worker_threads=fg_prep_sizer,
    )

    assert settings.workers == 2
    assert settings.batch_max == 2
    assert settings.prep_workers == 6
    assert settings.db_prefetch_workers == 4
    assert sizing_calls[-1] == {"inflight_limit": 8, "kind": "fg_prep"}

    settings = read_native_fg_pipeline_settings(
        inflight_limit=5,
        default_worker_threads=fg_prep_sizer,
    )

    assert settings.workers == 2
    assert settings.batch_max == 2
    assert settings.prep_workers == 5
    assert settings.db_prefetch_workers == 4

    settings = read_native_fg_pipeline_settings(
        inflight_limit=16,
        default_worker_threads=fg_prep_sizer,
    )

    assert settings.workers == 2
    assert settings.batch_max == 2
    assert settings.prep_workers == 6
    assert settings.db_prefetch_workers == 4


def test_read_native_fg_pipeline_settings_uses_canonical_db_prefetch():
    settings = read_native_fg_pipeline_settings(
        inflight_limit=8,
        default_worker_threads=lambda **_kwargs: 3,
    )

    assert settings.prep_workers == 3
    assert settings.db_prefetch_workers == 3


def test_inflight_base_pipeline_inflight_counts_done_unprocessed_futures():
    # Base admission gates on SLOT HOLDERS: a song whose future completed but
    # whose completion has not been processed still holds its slot, so it must
    # stay in (and be counted by) the inflight conveyor until popped.
    pipeline = InflightBasePipeline()
    active_song = make_native_song(task_key="base-active", song_name="Base Active")
    done_song = make_native_song(task_key="base-done", song_name="Base Done")
    active_future = Future()
    done_future = Future()
    done_future.set_result({"ok": True})

    pipeline.track_submitted(active_song, active_future, register_future=lambda _future: None)
    pipeline.track_submitted(done_song, done_future, register_future=lambda _future: None)

    assert len(pipeline.inflight) == 2

    completions = pipeline.pop_completed_searches()
    assert [c.song for c in completions] == [done_song]
    assert len(pipeline.inflight) == 1


def test_native_fg_pipeline_queue_pop_and_submit():
    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=2, batch_max=2, prep_workers=1))
    try:
        song = make_native_song(
            task_key="song-a",
            song_name="Song A",
            fg_prep_future=None,
            fg_queued_t0=None,
        )
        song.runtime.fg.fg_dynamic_prep_done = True

        pipeline.queue(song, now_s=10.0)

        assert len(pipeline.pending) == 1
        assert pipeline.ready_count() == 1
        assert abs(pipeline.oldest_wait_s(11.25) - 1.25) < 1e-9

        popped = pipeline.pop_next(allow_not_ready=False)
        assert popped is song
        assert len(pipeline.pending) == 0

        future = pipeline.submit_job(lambda queued_song, value: (queued_song.config.task_key, value), song, value=7)

        assert future.result(timeout=2) == ("song-a", 7)
        assert len(pipeline.futures) == 1
    finally:
        pipeline.shutdown_fg(wait=True, cancel_futures=True)
        pipeline.shutdown_prep(wait=True, cancel_futures=True)


def test_native_fg_pipeline_does_not_pop_unready_outside_final_drain():
    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=1, batch_max=1, prep_workers=1))
    try:
        prep_future = Future()
        song = make_native_song(task_key="song-b", song_name="Song B", fg_prep_future=prep_future, fg_queued_t0=None)

        pipeline.queue(song, now_s=20.0)

        assert pipeline.ready_count() == 0
        assert pipeline.pop_next(allow_not_ready=False) is None
        assert len(pipeline.pending) == 1

        popped = pipeline.pop_next(allow_not_ready=True)
        assert popped is song
        assert len(pipeline.pending) == 0

        pipeline.requeue_front(song)
        assert pipeline.pending[0] is song
    finally:
        pipeline.shutdown_fg(wait=True, cancel_futures=True)
        pipeline.shutdown_prep(wait=True, cancel_futures=True)


def test_native_fg_pipeline_pop_next_claims_prep_ownership():
    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=1, batch_max=1, prep_workers=1))
    try:
        prep_future = Future()
        prep_future.set_result(None)
        song = make_native_song(task_key="claim-prep", song_name="Claim Prep", fg_prep_future=prep_future)
        pipeline.queue(song, now_s=20.0)
        pipeline.prep_inflight.append(song)

        assert pipeline.pop_next(allow_not_ready=False) is song
        assert list(pipeline.pending) == []
        assert list(pipeline.prep_inflight) == []
    finally:
        pipeline.shutdown_fg(wait=True, cancel_futures=True)
        pipeline.shutdown_prep(wait=True, cancel_futures=True)


def test_native_fg_pipeline_pop_completed_jobs_keeps_future_result_policy_external():
    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=2, batch_max=2, prep_workers=1))
    try:
        completed_song = make_native_song(task_key="fg-done", song_name="FG Done")
        pending_song = make_native_song(task_key="fg-pending", song_name="FG Pending")
        completed_future = Future()
        completed_future.set_result("ok")
        pending_future = Future()
        pipeline.futures.extend(
            [
                (completed_song, completed_future, 10.0),
                (pending_song, pending_future, 20.0),
            ]
        )

        completions = pipeline.pop_completed_jobs()

        assert len(completions) == 1
        assert completions[0].song is completed_song
        assert completions[0].future is completed_future
        assert completions[0].submit_t0 == 10.0
        assert completions[0].future.result(timeout=0) == "ok"
        assert list(pipeline.futures) == [(pending_song, pending_future, 20.0)]
    finally:
        pipeline.shutdown_fg(wait=True, cancel_futures=True)
        pipeline.shutdown_prep(wait=True, cancel_futures=True)


def test_native_fg_pipeline_tops_up_pending_prep_without_fg_worker_waits():
    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=2, batch_max=2, prep_workers=2))
    release = threading.Event()
    started_keys: list[str] = []
    lock = threading.Lock()
    try:
        songs = [
            make_native_song(
                task_key=f"song-{idx}",
                song_name=f"Song {idx}",
                fg_prep_future=None,
                fg_queued_t0=None,
            )
            for idx in range(4)
        ]
        for song in songs:
            song.runtime.fg.fg_dynamic_prep_done = False
        for song in songs:
            pipeline.queue(song, now_s=1.0)

        def _prep(song, gpu_client=None):
            with lock:
                started_keys.append(song.config.task_key)
            release.wait(timeout=2)

        registered = []
        started = pipeline.start_pending_prep(
            _prep,
            gpu_client=None,
            max_new=4,
            register_future=registered.append,
        )

        deadline = time.monotonic() + 2.0
        while len(started_keys) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)

        assert started == 2
        assert len(registered) == 2
        assert set(started_keys) == {"song-0", "song-1"}
        assert pipeline.active_prep_count() == 2
        assert pipeline.has_active_prep() is True
        assert pipeline.start_pending_prep(_prep, gpu_client=None, max_new=4) == 0
        assert pipeline.pop_next(allow_not_ready=False) is None

        release.set()
        for song in songs[:2]:
            song.runtime.fg.fg_prep_future.result(timeout=2)
            song.runtime.fg.fg_dynamic_prep_done = True

        assert pipeline.pop_next(allow_not_ready=False) is songs[0]
        assert pipeline.start_pending_prep(_prep, gpu_client=None, max_new=4) == 2
    finally:
        release.set()
        pipeline.shutdown_fg(wait=True, cancel_futures=True)
        pipeline.shutdown_prep(wait=True, cancel_futures=True)


def test_native_fg_pipeline_finish_completed_prep_owns_future_drain_state():
    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=2, batch_max=2, prep_workers=2))
    try:
        success_future = Future()
        success_future.set_result(None)
        success = make_native_song(
            task_key="prep-ok",
            song_name="Prep OK",
            fg_prep_future=success_future,
            fg_prep_submit_t0=10.0,
            cpu_fg_prep_s=0.25,
        )

        failed_future = Future()
        failed_future.set_exception(RuntimeError("prep boom"))
        failed = make_native_song(
            task_key="prep-fail",
            song_name="Prep Fail",
            fg_prep_future=failed_future,
            fg_prep_submit_t0=20.0,
            cpu_fg_prep_s=0.5,
        )

        missing = make_native_song(task_key="prep-missing", song_name="Prep Missing")
        pipeline.pending.extend([success, failed, missing])
        pipeline.prep_inflight.extend([success, failed, missing])

        completions = pipeline.finish_completed_prep()

        assert [completion.song.config.task_key for completion in completions] == [
            "prep-ok",
            "prep-fail",
            "prep-missing",
        ]
        ok_completion, failed_completion, missing_completion = completions

        assert ok_completion.submit_t0 == 10.0
        assert ok_completion.cpu_seconds == 0.25
        assert ok_completion.error is None
        assert ok_completion.future_missing is False
        assert success.runtime.fg.fg_dynamic_prep_done is True
        assert success.runtime.fg.fg_prep_future is None
        assert success.runtime.fg.fg_prep_submit_t0 is None

        assert failed_completion.submit_t0 == 20.0
        assert failed_completion.cpu_seconds == 0.5
        assert isinstance(failed_completion.error, RuntimeError)
        assert "prep boom" in failed_completion.trace
        assert failed.runtime.fg.fg_dynamic_prep_done is False
        assert failed.runtime.fg.fg_prep_future is None
        assert failed.runtime.fg.fg_prep_submit_t0 is None

        assert missing_completion.future_missing is True
        assert isinstance(missing_completion.error, RuntimeError)
        assert "lost its future" in str(missing_completion.error)
        assert len(pipeline.prep_inflight) == 0
        assert list(pipeline.pending) == [success]
    finally:
        pipeline.shutdown_fg(wait=True, cancel_futures=True)
        pipeline.shutdown_prep(wait=True, cancel_futures=True)


def test_run_fg_job_sync_fails_at_prep_future_error_not_missing_plan():
    prep_future = Future()
    prep_future.set_exception(RuntimeError("prep exploded"))
    song = make_native_song(
        task_key="prep-fail-song",
        song_name="Prep Fail Song",
        fg_prep_future=prep_future,
    )

    with pytest.raises(RuntimeError, match="FG dynamic prep failed for prep-fail-song") as excinfo:
        run_fg_job_sync(song, gpu_client=object())

    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert "prep exploded" in str(excinfo.value.__cause__)
    assert song.runtime.fg.fg_prep_future is None


def test_run_fg_job_sync_requires_dynamic_prep_future_to_materialize_plan():
    prep_future = Future()
    prep_future.set_result(None)
    song = make_native_song(
        task_key="prep-no-plan",
        song_name="Prep No Plan",
        fg_prep_future=prep_future,
    )

    with pytest.raises(RuntimeError, match="FG dynamic prep failed for prep-no-plan") as excinfo:
        run_fg_job_sync(song, gpu_client=object())

    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert "completed without the exact response frontier plan" in str(excinfo.value.__cause__)
    assert song.runtime.fg.fg_prep_future is None
    assert song.runtime.fg.fg_dynamic_prep_done is False


def test_claim_pending_song_never_invokes_song_equality_or_repr():
    class _HostileSong:
        # deque.remove would trip both hazards: __eq__ while scanning past other
        # queued songs, and repr() rendered into the not-found ValueError message
        # (a full NativeSong repr is tens of seconds of CPU, paid per claim).
        def __eq__(self, other):
            raise AssertionError("song equality must not be used by claim")

        def __repr__(self):
            raise AssertionError("song repr must not be rendered by claim")

        __hash__ = object.__hash__

    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=1, batch_max=1, prep_workers=1))
    try:
        other = _HostileSong()
        target = _HostileSong()
        pipeline.pending.append(other)
        pipeline.pending.append(target)
        # target is intentionally NOT in prep_inflight: prep typically finished
        # before the claim, so the removal there must tolerate absence cheaply.
        claimed = pipeline._claim_pending_song(target)

        assert claimed is target
        assert len(pipeline.pending) == 1
        assert pipeline.pending[0] is other
        assert len(pipeline.prep_inflight) == 0
    finally:
        pipeline.shutdown_fg(wait=True, cancel_futures=True)
        pipeline.shutdown_prep(wait=True, cancel_futures=True)
