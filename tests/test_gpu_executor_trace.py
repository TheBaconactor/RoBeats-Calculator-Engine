from pathlib import Path

from gear_optimizer.solver import gpu_executor_profile
from gear_optimizer.solver.gpu_executor_profile import ExecutorTraceWriter, TRACE_HEADER


def test_executor_trace_writer_opens_file_with_header(tmp_path: Path):
    trace_path = tmp_path / "gpu_executor_trace.csv"
    writer = ExecutorTraceWriter()

    writer.open(str(trace_path))
    try:
        assert writer.has_file is True
        assert trace_path.read_text(encoding="utf-8") == TRACE_HEADER
    finally:
        writer.close()

    assert writer.has_file is False


def test_executor_trace_writer_writes_csv_and_profile_event(tmp_path: Path, monkeypatch):
    trace_path = tmp_path / "gpu_executor_trace.csv"
    writer = ExecutorTraceWriter()
    events = []
    monkeypatch.setattr(gpu_executor_profile, "emit_profile_event", lambda **kwargs: events.append(kwargs))

    writer.open(str(trace_path))
    try:
        writer.write_event(
            event="running",
            in_process=True,
            wait_sec=0.125,
            exec_sec=0.5,
            batch_size=3,
            types="gpu_native_ga_run:3",
            planner_mode="inproc",
            queue_depth_hint=4,
            pressure_hint=0.25,
            work_units=12.5,
            dominant_type="gpu_native_ga_run",
            dominant_share_pct=100.0,
            diversity_pct=10.0,
            avg_submit_age_ms=1.5,
        )
    finally:
        writer.close()

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == TRACE_HEADER.strip()
    assert ",running,0.125000,0.500000,3,gpu_native_ga_run:3,1,inproc,4,0.250,12.500," in lines[1]
    assert events
    assert events[0]["component"] == "gpu_executor"
    assert events[0]["event"] == "trace::running"
    assert events[0]["metrics"]["in_process"] == 1
