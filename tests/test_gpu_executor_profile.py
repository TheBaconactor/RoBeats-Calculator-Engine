import json

from gear_optimizer.solver.gpu_executor_profile import (
    ExecutorTraceWriter,
    batch_trace_context,
    estimate_request_work_units,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def test_executor_trace_writer_is_inert_without_path(tmp_path):
    writer = ExecutorTraceWriter()

    writer.open("")
    writer.write_event(event="wait", wait_sec=0.25)
    writer.close()

    assert writer.has_file is False
    assert not list(tmp_path.iterdir())


def test_executor_trace_writer_writes_jsonl_events(tmp_path):
    trace_path = tmp_path / "trace" / "gpu_executor_trace.jsonl"
    writer = ExecutorTraceWriter()

    writer.open(str(trace_path))
    assert writer.has_file is True
    writer.write_event(event="wait", wait_sec=0.25, batch_size=3)
    writer.write("exec", exec_sec=1.5, types="force_greats_response_frontier_score_batch:1")
    writer.close()
    assert writer.has_file is False

    rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert [row["event"] for row in rows] == ["wait", "exec"]
    assert rows[0]["wait_sec"] == 0.25
    assert rows[0]["batch_size"] == 3
    assert rows[1]["exec_sec"] == 1.5
    assert rows[1]["types"] == "force_greats_response_frontier_score_batch:1"
    assert all(isinstance(row["ts_wall"], float) for row in rows)


def test_batch_trace_context_does_not_duplicate_explicit_event_fields():
    context = batch_trace_context(
        {
            "batch_size": 7,
            "types": "gpu_native_ga_run:7",
            "queue_depth_hint": 11,
            "pressure_hint": 0.5,
        }
    )

    assert "batch_size" not in context
    assert "types" not in context
    assert context == {"queue_depth_hint": 11, "pressure_hint": 0.5}


def test_estimate_request_work_units_uses_native_ga_shape():
    request = GpuRequest(
        request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
        request_id=1,
        worker_id=0,
        payload={"num_runs": 3, "n_genomes": 512, "n_generations": 40},
    )

    assert estimate_request_work_units(request) == 61440.0


def test_estimate_request_work_units_falls_back_to_payload_size_hint():
    request = GpuRequest(
        request_type=GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH,
        request_id=2,
        worker_id=0,
        payload={"tasks": [1, 2, 3]},
    )

    assert estimate_request_work_units(request) == 3.0
