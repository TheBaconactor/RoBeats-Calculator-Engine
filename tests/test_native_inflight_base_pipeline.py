from __future__ import annotations

from concurrent.futures import Future
from types import SimpleNamespace

from gear_optimizer.solver.native_inflight_pipeline import BaseDecodeQueue, InflightBasePipeline
from gear_optimizer.solver.native_fg_owner import ExactBaseOwnerResult
from tests.native_song_factory import make_native_song


def test_base_decode_queue_submit_and_pop_completed_keeps_result_policy_external():
    queue = BaseDecodeQueue(max_workers=1)
    try:
        song = make_native_song(task_key="song-a", song_name="Song A")
        registered = []

        def _decode(queued_song, base_result):
            return queued_song.config.task_key, base_result["score"]

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


def test_base_decode_queue_cancel_all_cancels_inflight_decode_futures():
    queue = BaseDecodeQueue(max_workers=1)
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


def test_inflight_base_pipeline_tracks_and_pops_completed_searches_without_consuming_result():
    pipeline = InflightBasePipeline()
    completed = make_native_song(task_key="base-done", song_name="Base Done")
    pending = make_native_song(task_key="base-pending", song_name="Base Pending")
    completed_future = Future()
    completed_future.set_result({"score": 1})
    pending_future = Future()
    registered = []

    pipeline.track_submitted(completed, completed_future, register_future=registered.append)
    pipeline.track_submitted(pending, pending_future, register_future=registered.append)

    assert registered == [completed_future, pending_future]
    assert completed.runtime.base.base_future is completed_future
    assert list(pipeline.inflight) == [completed, pending]

    completions = pipeline.pop_completed_searches()

    assert len(completions) == 1
    assert completions[0].song is completed
    assert completions[0].future is completed_future
    assert completions[0].future.result(timeout=0) == {"score": 1}
    assert list(pipeline.inflight) == [pending]


def test_decode_base_result_sync_requires_typed_fused_owner_result(monkeypatch):
    from gear_optimizer.solver import native_inflight_pipeline as pipeline_module

    song = make_native_song(task_key="base-result", solver_context=object())
    expected = ({"Score": 1}, [], [], [{"BaseScore": 1}])
    base_result = object()
    owner_score = {(1, 2, 3, 4, 5, 6, 7): object()}
    monkeypatch.setattr(
        pipeline_module,
        "decode_exact_base_pipeline_result",
        lambda *, result, context: expected if result is base_result else None,
    )

    decoded = pipeline_module.decode_base_result_sync(
        song,
        ExactBaseOwnerResult(base_result=base_result, fg_owner_score=owner_score),
    )

    assert decoded == expected
    assert song.runtime.fg.fg_owner_score_map is owner_score

    try:
        pipeline_module.decode_base_result_sync(song, {"base_result": base_result})
    except TypeError as exc:
        assert "ExactBaseOwnerResult" in str(exc)
    else:
        raise AssertionError("legacy dict owner response must be rejected")


def test_inflight_base_payload_contains_only_exact_search_and_native_fg_inputs():
    context = SimpleNamespace(song_slot=2)
    domains = object()
    song_context = object()
    timeline_frontier = object()
    fg_bundle = object()
    fg_calc_song = {
        "metadata": {"Last Note Time": 1.0, "Long Notes": 0},
        "song_data": {"timestamps": [0.0, 1.0], "note_types": [1, 1], "lanes": [0, 1]},
    }
    song = make_native_song(
        song_slot=2,
        solver_context=context,
        exact_base_domains=domains,
        exact_base_song_context=song_context,
        timeline_frontier=timeline_frontier,
        calc_song=fg_calc_song,
        fg_calc_song=fg_calc_song,
        fg_response_scoring_bundle=fg_bundle,
    )

    payload = InflightBasePipeline.build_payload(song)

    assert payload == {
        "context": context,
        "domains": domains,
        "song_context": song_context,
        "timeline_frontier": timeline_frontier,
        "candidate_limit": 51,
        "fg_scoring_bundle": fg_bundle,
        "fg_calc_song": fg_calc_song,
    }
    assert not any("ga" in key.lower() for key in payload)
