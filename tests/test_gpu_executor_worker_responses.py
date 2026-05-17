import queue

import pytest

from gear_optimizer.solver.gpu_executor_types import GpuResponse
from gear_optimizer.solver.gpu_executor_lifecycle import WorkerResponseRouter


def test_worker_response_router_waits_for_matching_response():
    router = WorkerResponseRouter(pending_ttl_sec=0.0, pending_max=16)
    response = GpuResponse(request_id=17, success=True, result={"ok": True})

    router.store(response)

    assert router.wait(17, 0.01) is response


def test_worker_response_router_prunes_oldest_when_max_exceeded():
    router = WorkerResponseRouter(pending_ttl_sec=0.0, pending_max=2)

    router.store(GpuResponse(request_id=1, success=True))
    router.store(GpuResponse(request_id=2, success=True))
    router.store(GpuResponse(request_id=3, success=True))

    with pytest.raises(RuntimeError, match="GPU executor timeout"):
        router.wait(1, 0.001)
    assert router.wait(2, 0.01).request_id == 2
    assert router.wait(3, 0.01).request_id == 3


def test_worker_response_router_thread_reads_current_queue():
    router = WorkerResponseRouter(pending_ttl_sec=0.0, pending_max=16)
    responses: queue.Queue = queue.Queue()
    router.ensure_started(lambda: responses, label="pytest")

    try:
        responses.put(GpuResponse(request_id=44, success=True, result="done"))

        assert router.wait(44, 1.0).result == "done"
    finally:
        router.reset()
