import json

from gear_optimizer.solver.gpu_executor_lifecycle import ExecutorHeartbeatWriter, summarize_request_batch
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(request_type: GpuRequestType, request_id: int) -> GpuRequest:
    return GpuRequest(
        request_type=request_type,
        request_id=request_id,
        worker_id=0,
        payload={},
    )


def test_summarize_request_batch_ignores_shutdown_requests():
    type_counts, request_count = summarize_request_batch(
        [
            _request(GpuRequestType.LOAD_REF_ARRAYS, 1),
            _request(GpuRequestType.LOAD_REF_ARRAYS, 2),
            _request(GpuRequestType.SHUTDOWN, 3),
        ]
    )

    assert request_count == 2
    assert type_counts == {"load_ref_arrays": 2}


def test_executor_heartbeat_writer_writes_compact_payload(tmp_path):
    heartbeat_path = tmp_path / "executor_heartbeat.json"
    writer = ExecutorHeartbeatWriter(path=heartbeat_path, interval_sec=10.0)

    writer.write(
        phase="running",
        batch=[_request(GpuRequestType.EXACT_BASE_SEARCH, 10)],
        ready=True,
        running=True,
        requests_processed=12,
        response_put_failures_total=3,
        force=True,
    )

    payload = json.loads(heartbeat_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "running"
    assert payload["ready"] is True
    assert payload["running"] is True
    assert payload["requests_processed"] == 12
    assert payload["request_count"] == 1
    assert payload["request_types"] == {"exact_base_search": 1}
    assert payload["response_put_failures_total"] == 3


def test_executor_heartbeat_writer_throttles_same_phase(tmp_path):
    heartbeat_path = tmp_path / "executor_heartbeat.json"
    writer = ExecutorHeartbeatWriter(path=heartbeat_path, interval_sec=1000.0)

    writer.write(
        phase="idle",
        ready=True,
        running=True,
        requests_processed=1,
        response_put_failures_total=0,
        force=True,
    )
    first = json.loads(heartbeat_path.read_text(encoding="utf-8"))

    writer.write(
        phase="idle",
        ready=True,
        running=True,
        requests_processed=99,
        response_put_failures_total=0,
        force=False,
    )
    second = json.loads(heartbeat_path.read_text(encoding="utf-8"))

    assert second["requests_processed"] == first["requests_processed"]
