from gear_optimizer.solver.native_inflight_lifecycle import (
    ActiveRuntimeProgressReporter,
    ProgressTracker,
    evaluate_fg_progress_record_update,
)
from gear_optimizer.solver.native_inflight_config import make_native_song


def test_progress_tracker_emit_progress_is_best_effort():
    tracker = ProgressTracker()

    def _raise_progress(**_kwargs):
        raise RuntimeError("ui callback failed")

    tracker.emit_progress(
        _raise_progress,
        completed_delta=1,
        record_info={"status": "DONE"},
    )


def test_progress_tracker_emit_progress_forwards_payload():
    tracker = ProgressTracker()
    seen = {}

    def _capture_progress(**kwargs):
        seen.update(kwargs)

    tracker.emit_progress(
        _capture_progress,
        completed_delta=2,
        failed_delta=1,
        record_info={"song": "demo"},
    )

    assert seen == {
        "completed_delta": 2,
        "failed_delta": 1,
        "record_info": {"song": "demo"},
    }


def test_progress_tracker_emit_error_item_progress_forwards_failure():
    tracker = ProgressTracker()
    events = []

    emitted = tracker.emit_error_item_progress(
        lambda **kwargs: events.append(kwargs),
        {"_error": True, "_queue_label": "song-a"},
    )

    assert emitted is True
    assert events == [
        {
            "completed_delta": 1,
            "failed_delta": 1,
            "record_info": {"song": "song-a", "status": "FAILED"},
        }
    ]


def test_progress_tracker_emit_error_item_progress_ignores_suppressed_or_non_errors():
    tracker = ProgressTracker()
    events = []

    assert tracker.emit_error_item_progress(lambda **kwargs: events.append(kwargs), {"_error": True, "_suppress_progress": True}) is False
    assert tracker.emit_error_item_progress(lambda **kwargs: events.append(kwargs), {"song": "song-a"}) is False
    assert tracker.emit_error_item_progress(lambda **kwargs: events.append(kwargs), "not-a-payload") is False
    assert events == []


def test_progress_tracker_emit_done_song_progress_defaults_done_record():
    tracker = ProgressTracker()
    events = []
    song = make_native_song(task_key="done-song", song_name="Done Song")

    tracker.emit_done_song_progress(lambda **kwargs: events.append(kwargs), song)

    assert events == [
        {
            "completed_delta": 1,
            "failed_delta": 0,
            "record_info": {"song": "done-song", "status": "DONE"},
        }
    ]


def test_progress_tracker_done_record_info_preserves_existing_fields():
    song = make_native_song(task_key="done-song", song_name="Done Song")
    song.runtime.db.record_info = {"song": "custom", "score": 123}

    assert ProgressTracker.done_record_info_for_song(song) == {
        "song": "custom",
        "score": 123,
        "status": "DONE",
    }


def test_progress_tracker_seed_valid_baseline_ignores_invalid_baseline():
    tracker = ProgressTracker()

    tracker.seed_valid_baseline("song-a", best_score=1000, best_fg=900, baseline_valid=False)
    assert tracker.snapshot("song-a") == (0, 0, False)

    tracker.seed_valid_baseline("song-a", best_score=1000, best_fg=900, baseline_valid=True)
    assert tracker.snapshot("song-a") == (1000, 900, True)


def test_progress_tracker_evaluate_record_update_updates_session_best():
    tracker = ProgressTracker()
    tracker.seed_valid_baseline("song-a", best_score=1000, best_fg=900, baseline_valid=True)

    record_info = tracker.evaluate_record_update(
        "song-a",
        {"BaseScore": 1003},
        [],
    )

    assert isinstance(record_info, dict)
    assert record_info["is_better"] is True
    assert tracker.snapshot("song-a") == (1003, 900, True)


def test_progress_tracker_evaluate_record_update_updates_fg_session_best():
    tracker = ProgressTracker()
    tracker.seed_valid_baseline("song-a", best_score=1000, best_fg=900, baseline_valid=True)

    record_info = tracker.evaluate_record_update(
        "song-a",
        {"BaseScore": 1000},
        [{"base_score": 1000, "fg_score": 1050, "data": {"ForceGreats": {"config": {"a": 1}}}}],
    )

    assert isinstance(record_info, dict)
    assert record_info["is_fg_better"] is True
    assert tracker.snapshot("song-a") == (1000, 1050, True)


def test_evaluate_fg_progress_record_update_uses_tracker_snapshot_and_updates_fg_best():
    tracker = ProgressTracker()
    tracker.seed_valid_baseline("song-a", best_score=1000, best_fg=900, baseline_valid=True)
    song = make_native_song(
        db_key="song-a",
        task_key="Song A (Hard)",
        best_data={"BaseScore": 1000},
        fg_variants=[
            {
                "base_score": 1000,
                "fg_score": 1050,
                "data": {"ForceGreats": {"config": {"NonFever1": 1}}},
            }
        ],
        db_best_score=1,
        db_best_fg_score=1,
        db_baseline_valid=False,
    )

    record_info = evaluate_fg_progress_record_update(song, tracker)

    assert isinstance(record_info, dict)
    assert record_info["is_fg_better"] is True
    assert record_info["song"] == "Song A (Hard)"
    assert tracker.snapshot("song-a") == (1000, 1050, True)


def test_active_runtime_progress_reporter_prefers_ga_then_decode_then_fg():
    ga_song = make_native_song(task_key="ga-song", song_name="GA Song")
    decode_song = make_native_song(task_key="decode-song", song_name="Decode Song")
    fg_song = make_native_song(task_key="fg-song", song_name="FG Song")

    assert (
        ActiveRuntimeProgressReporter.active_song_label(
            ga_inflight=[ga_song],
            decode_inflight=[decode_song],
            fg_futures=[(fg_song, object(), 0.0)],
        )
        == "ga-song"
    )
    assert (
        ActiveRuntimeProgressReporter.active_song_label(
            ga_inflight=[],
            decode_inflight=[decode_song],
            fg_futures=[(fg_song, object(), 0.0)],
        )
        == "decode-song"
    )
    assert (
        ActiveRuntimeProgressReporter.active_song_label(
            ga_inflight=[],
            decode_inflight=[],
            fg_futures=[(fg_song, object(), 0.0)],
        )
        == "fg-song"
    )


def test_active_runtime_progress_reporter_emits_running_only_on_change_unless_forced():
    events = []
    reporter = ActiveRuntimeProgressReporter(lambda **kwargs: events.append(kwargs))
    song = make_native_song(task_key="demo-song", song_name="Demo Song")

    reporter.emit(ga_inflight=[song], decode_inflight=[], fg_futures=[])
    reporter.emit(ga_inflight=[song], decode_inflight=[], fg_futures=[])
    reporter.emit(ga_inflight=[song], decode_inflight=[], fg_futures=[], force=True)

    assert events == [
        {
            "completed_delta": 0,
            "failed_delta": 0,
            "record_info": {"song": "demo-song", "status": "RUNNING"},
        },
        {
            "completed_delta": 0,
            "failed_delta": 0,
            "record_info": {"song": "demo-song", "status": "RUNNING"},
        },
    ]
