from __future__ import annotations

import threading
import time
from concurrent.futures import Future

from gear_optimizer.solver.native_inflight_fg_pipeline import (
    NativeFGPipeline,
    NativeFGPipelineSettings,
    read_native_fg_pipeline_settings,
)
from gear_optimizer.solver.native_inflight_types import make_native_song


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
