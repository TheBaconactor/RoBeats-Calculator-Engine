from __future__ import annotations

import threading
import time
from concurrent.futures import Future

from gear_optimizer.solver.native_inflight_pipeline import (
    NativeFGPipeline,
    NativeFGPipelineSettings,
    read_native_fg_pipeline_settings,
)
from gear_optimizer.solver.native_inflight_config import make_native_song


def test_read_native_fg_pipeline_settings_defaults_and_overrides(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_WORKERS", raising=False)
    monkeypatch.delenv("INFLIGHT_FG_BATCH_MAX", raising=False)
    monkeypatch.delenv("INFLIGHT_FG_PREP_WORKERS", raising=False)

    settings = read_native_fg_pipeline_settings(
        None,
        inflight_limit=8,
        ga_credit_budget_cfg=12,
        default_worker_threads=lambda **_kwargs: 3,
    )

    assert settings.workers == 8
    assert settings.batch_max == 8
    assert settings.prep_workers == 3
    assert settings.ga_credit_budget == 12
    assert settings.static_prep_max_inflight == 0
    assert settings.db_prefetch_workers == 3

    monkeypatch.setenv("INFLIGHT_FG_WORKERS", "9")
    monkeypatch.setenv("INFLIGHT_FG_BATCH_MAX", "6")
    monkeypatch.setenv("INFLIGHT_FG_PREP_WORKERS", "7")
    settings = read_native_fg_pipeline_settings(
        None,
        inflight_limit=5,
        ga_credit_budget_cfg=2,
        default_worker_threads=lambda **_kwargs: 1,
    )

    assert settings.workers == 5
    assert settings.batch_max == 5
    assert settings.prep_workers == 5
    assert settings.ga_credit_budget == 2
    assert settings.db_prefetch_workers == 4

    monkeypatch.setenv("INFLIGHT_FG_WORKERS", "12")
    monkeypatch.setenv("INFLIGHT_FG_BATCH_MAX", "12")
    monkeypatch.setenv("INFLIGHT_FG_PREP_WORKERS", "12")
    settings = read_native_fg_pipeline_settings(
        None,
        inflight_limit=16,
        ga_credit_budget_cfg=2,
        default_worker_threads=lambda **_kwargs: 1,
    )

    assert settings.workers == 8
    assert settings.batch_max == 8
    assert settings.prep_workers == 8
    assert settings.db_prefetch_workers == 4


def test_read_native_fg_pipeline_settings_includes_static_prep_and_db_prefetch(monkeypatch):
    monkeypatch.delenv("INFLIGHT_FG_WORKERS", raising=False)
    monkeypatch.delenv("INFLIGHT_FG_BATCH_MAX", raising=False)
    monkeypatch.delenv("INFLIGHT_FG_PREP_WORKERS", raising=False)
    monkeypatch.delenv("INFLIGHT_FG_STATIC_PREP_MAX_INFLIGHT", raising=False)
    monkeypatch.delenv("INFLIGHT_DB_PREFETCH_WORKERS", raising=False)
    monkeypatch.setenv("INFLIGHT_DB_PREFETCH_WORKERS", "6")

    settings = read_native_fg_pipeline_settings(
        None,
        inflight_limit=8,
        ga_credit_budget_cfg=2,
        cpu_prewarm_lookahead=5,
        default_worker_threads=lambda **_kwargs: 3,
    )

    assert settings.prep_workers == 3
    assert settings.static_prep_max_inflight == 3
    assert settings.db_prefetch_workers == 6


def test_native_fg_pipeline_queue_pop_credit_and_submit():
    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=2, batch_max=2, prep_workers=1, ga_credit_budget=2))
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

        pipeline.note_ga_submit()
        assert pipeline.ga_credit == 1
        pipeline.note_ga_submit()
        assert pipeline.ga_credit == 0

        popped = pipeline.pop_next(allow_not_ready=False)
        assert popped is song
        assert len(pipeline.pending) == 0

        future = pipeline.submit_job(lambda queued_song, value: (queued_song.config.task_key, value), song, value=7)

        assert future.result(timeout=2) == ("song-a", 7)
        assert len(pipeline.futures) == 1
        assert pipeline.ga_credit == 2
    finally:
        pipeline.shutdown_fg(wait=True, cancel_futures=True)
        pipeline.shutdown_prep(wait=True, cancel_futures=True)


def test_native_fg_pipeline_does_not_pop_unready_without_slot_pressure():
    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=1, batch_max=1, prep_workers=1, ga_credit_budget=1))
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


def test_native_fg_pipeline_pop_completed_jobs_keeps_future_result_policy_external():
    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=2, batch_max=2, prep_workers=1, ga_credit_budget=1))
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
    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=2, batch_max=2, prep_workers=2, ga_credit_budget=1))
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
    pipeline = NativeFGPipeline(NativeFGPipelineSettings(workers=2, batch_max=2, prep_workers=2, ga_credit_budget=1))
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
        assert missing_completion.error is None
        assert len(pipeline.prep_inflight) == 0
    finally:
        pipeline.shutdown_fg(wait=True, cancel_futures=True)
        pipeline.shutdown_prep(wait=True, cancel_futures=True)


def test_native_fg_pipeline_static_prep_budget_reserves_dynamic_prep_workers():
    pipeline = NativeFGPipeline(
        NativeFGPipelineSettings(
            workers=2,
            batch_max=2,
            prep_workers=3,
            ga_credit_budget=1,
            static_prep_max_inflight=3,
        )
    )
    try:
        assert pipeline.static_prep_budget() == 3

        pipeline.prep_inflight.append(make_native_song(task_key="dynamic-a", song_name="Dynamic A"))
        assert pipeline.static_prep_budget() == 2

        pipeline.prep_inflight.append(make_native_song(task_key="dynamic-b", song_name="Dynamic B"))
        pipeline.prep_inflight.append(make_native_song(task_key="dynamic-c", song_name="Dynamic C"))
        assert pipeline.static_prep_budget() == 0
    finally:
        pipeline.shutdown_fg(wait=True, cancel_futures=True)
        pipeline.shutdown_prep(wait=True, cancel_futures=True)


def test_native_fg_pipeline_start_static_prep_counts_external_and_owned_lanes():
    pipeline = NativeFGPipeline(
        NativeFGPipelineSettings(
            workers=2,
            batch_max=2,
            prep_workers=2,
            ga_credit_budget=1,
            static_prep_max_inflight=2,
        )
    )
    release = threading.Event()
    external = None
    try:
        disabled = make_native_song(task_key="disabled", song_name="Disabled")
        assert pipeline.start_static_prep(disabled, lambda _song: None) is False
        assert disabled.runtime.fg.fg_static_prep_future is None

        external = make_native_song(
            task_key="external",
            song_name="External",
            manual_force_greats=True,
        )
        external.runtime.fg.fg_static_prep_future = Future()
        pipeline.pending.append(external)

        song = make_native_song(
            task_key="static-a",
            song_name="Static A",
            manual_force_greats=True,
        )
        registered: list[Future] = []

        def _static_prep(_song):
            release.wait(timeout=2)

        assert (
            pipeline.start_static_prep(
                song,
                _static_prep,
                external_song_groups=([external],),
                register_future=registered.append,
            )
            is True
        )
        assert len(registered) == 1
        assert song.runtime.fg.fg_static_prep_future is registered[0]
        assert pipeline.active_static_prep_count([external, song]) == 2

        blocked = make_native_song(
            task_key="static-b",
            song_name="Static B",
            manual_force_greats=True,
        )
        assert pipeline.start_static_prep(blocked, _static_prep, external_song_groups=([song],)) is False
        assert blocked.runtime.fg.fg_static_prep_future is None
    finally:
        release.set()
        if external is not None and isinstance(external.runtime.fg.fg_static_prep_future, Future):
            external.runtime.fg.fg_static_prep_future.set_result(None)
        pipeline.shutdown_fg(wait=True, cancel_futures=True)
        pipeline.shutdown_prep(wait=True, cancel_futures=True)
