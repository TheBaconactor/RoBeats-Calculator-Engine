from __future__ import annotations

from concurrent.futures import Future

from gear_optimizer.solver.native_inflight_pipeline import GADecodeQueue, InflightGAPipeline
from tests.native_song_factory import make_native_song


def test_ga_decode_queue_submit_and_pop_completed_keeps_result_policy_external():
    queue = GADecodeQueue(max_workers=1)
    try:
        song = make_native_song(task_key="song-a", song_name="Song A")
        registered = []

        def _decode(queued_song, ga_result):
            return queued_song.config.task_key, ga_result["score"]

        future = queue.submit(
            song,
            {"score": 123},
            _decode,
            register_future=registered.append,
        )
        assert registered == [future]
        assert song.runtime.decode.decode_future is future
        assert song.runtime.decode.decode_submit_t0 is not None
        assert len(queue.inflight) == 1

        assert future.result(timeout=2) == ("song-a", 123)
        completions = queue.pop_completed()

        assert len(completions) == 1
        assert completions[0].song is song
        assert completions[0].future is future
        assert completions[0].submit_t0 == song.runtime.decode.decode_submit_t0
        assert len(queue.inflight) == 0
    finally:
        queue.shutdown(wait=True, cancel_futures=True)


def test_ga_decode_queue_cancel_all_cancels_inflight_decode_futures():
    queue = GADecodeQueue(max_workers=1)
    try:
        song = make_native_song(task_key="song-b", song_name="Song B")
        future = Future()
        song.runtime.decode.decode_future = future
        queue.inflight.append(song)

        queue.cancel_all()

        assert future.cancelled() is True
        assert len(queue.inflight) == 1
    finally:
        queue.shutdown(wait=True, cancel_futures=True)


def test_inflight_ga_pipeline_tracks_and_pops_completed_runs_without_consuming_result():
    pipeline = InflightGAPipeline()
    completed = make_native_song(
        task_key="ga-done",
        song_name="GA Done",
        ga_initial_populations=[{"seed": 1}],
    )
    pending = make_native_song(task_key="ga-pending", song_name="GA Pending")
    completed_future = Future()
    completed_future.set_result({"score": 1})
    pending_future = Future()
    registered = []

    pipeline.track_submitted(completed, completed_future, register_future=registered.append)
    pipeline.track_submitted(pending, pending_future, register_future=registered.append)

    assert registered == [completed_future, pending_future]
    assert completed.runtime.ga.ga_future is completed_future
    assert completed.runtime.ga.ga_initial_populations is None
    assert list(pipeline.inflight) == [completed, pending]

    completions = pipeline.pop_completed_runs()

    assert len(completions) == 1
    assert completions[0].song is completed
    assert completions[0].future is completed_future
    assert completions[0].future.result(timeout=0) == {"score": 1}
    assert list(pipeline.inflight) == [pending]
