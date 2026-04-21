from __future__ import annotations

from concurrent.futures import Future
from types import SimpleNamespace

from gear_optimizer.solver.native_inflight_fg_pipeline import (
    NativeFGPipeline,
    NativeFGPipelineSettings,
    read_native_fg_pipeline_settings,
)


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
        song = SimpleNamespace(task_key="song-a", song_name="Song A", fg_prep_future=None, fg_queued_t0=None)

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

        future = pipeline.submit_job(lambda queued_song, value: (queued_song.task_key, value), song, value=7)

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
        song = SimpleNamespace(task_key="song-b", song_name="Song B", fg_prep_future=prep_future, fg_queued_t0=None)

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
