from gear_optimizer.solver.gpu_executor_fg_frontier import execute_fg_select_signature_frontier_batch
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(payload) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.FG_SELECT_SIGNATURE_FRONTIER_BATCH,
        request_id=40,
        worker_id=0,
        payload=payload,
    )


def test_execute_fg_select_signature_frontier_batch_requires_in_process_queues():
    response = execute_fg_select_signature_frontier_batch(
        _request({"payloads": []}),
        in_process_queues=False,
        select_fn=lambda _payloads: [],
    )

    assert response.success is False
    assert "requires in-process queues" in str(response.error)


def test_execute_fg_select_signature_frontier_batch_requires_payload_list():
    response = execute_fg_select_signature_frontier_batch(
        _request({"payloads": ("not", "a", "list")}),
        in_process_queues=True,
        select_fn=lambda _payloads: [],
    )

    assert response.success is False
    assert "payload['payloads'] list" in str(response.error)


def test_execute_fg_select_signature_frontier_batch_forwards_payloads():
    calls = []
    payloads = [{"limit": 2}]

    def select_fn(payloads_arg):
        calls.append(payloads_arg)
        return ["frontier"]

    response = execute_fg_select_signature_frontier_batch(
        _request({"payloads": payloads}),
        in_process_queues=True,
        select_fn=select_fn,
    )

    assert response.success is True
    assert response.result == ["frontier"]
    assert calls == [payloads]
