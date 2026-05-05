from gear_optimizer.solver.native_inflight_progress import ProgressTracker


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
