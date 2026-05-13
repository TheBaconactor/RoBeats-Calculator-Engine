from gear_optimizer.solver.native_inflight_abort_log import (
    append_native_abort_log,
    build_abort_queue_snapshot,
    log_native_abort,
)


def test_build_abort_queue_snapshot_uses_native_queue_labels():
    assert build_abort_queue_snapshot(
        pending_tasks=1,
        prepared=2,
        prep_inflight=3,
        ga_inflight=4,
        decode_inflight=5,
        pending_fg=6,
        fg_prep=7,
        fg_futures=8,
    ) == (
        "pending=1 prepared=2 prep_inflight=3 ga_inflight=4 decode_inflight=5 "
        "pending_fg=6 fg_prep=7 fg_futures=8"
    )


def test_append_native_abort_log_writes_exception_snapshot_and_trace(tmp_path):
    path = tmp_path / "abort.log"

    written = append_native_abort_log(
        ValueError("boom"),
        snapshot="pending=1 prepared=0",
        trace="TRACE",
        path=path,
        timestamp="2026-05-12 12:00:00",
    )

    assert written is True
    text = path.read_text(encoding="utf-8")
    assert "[2026-05-12 12:00:00] ValueError: boom" in text
    assert "pending=1 prepared=0" in text
    assert "TRACE" in text


def test_log_native_abort_builds_snapshot_and_writes_log(tmp_path):
    path = tmp_path / "abort.log"

    written = log_native_abort(
        RuntimeError("boom"),
        pending_tasks=1,
        prepared=2,
        prep_inflight=3,
        ga_inflight=4,
        decode_inflight=5,
        pending_fg=6,
        fg_prep=7,
        fg_futures=8,
        trace="TRACE",
        path=path,
        timestamp="2026-05-12 12:00:00",
    )

    assert written is True
    text = path.read_text(encoding="utf-8")
    assert "[2026-05-12 12:00:00] RuntimeError: boom" in text
    assert "pending=1 prepared=2 prep_inflight=3 ga_inflight=4 decode_inflight=5" in text
    assert "pending_fg=6 fg_prep=7 fg_futures=8" in text
    assert "TRACE" in text
