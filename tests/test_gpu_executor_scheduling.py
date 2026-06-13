from __future__ import annotations

from collections import deque
from queue import Queue

from gear_optimizer.solver.gpu_executor import GpuExecutor
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(request_type: GpuRequestType, request_id: int) -> GpuRequest:
    return GpuRequest(
        request_type=request_type,
        request_id=int(request_id),
        worker_id=0,
        payload={},
    )


def test_gather_batch_keeps_adjacent_ga_requests_in_one_owner_turn():
    # Adjacent GA runs coalesce into one owner turn. Each GA run carries its own fused
    # GA->FG owner continuation (Slice 3), so there is no separate FG batch request to
    # interleave between them anymore.
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor._in_process_queues = True
    executor._request_queue = Queue()
    executor._staged_requests = deque()
    executor._request_queue.put(_request(GpuRequestType.GPU_NATIVE_GA_RUN, 1))
    executor._request_queue.put(_request(GpuRequestType.GPU_NATIVE_GA_RUN, 2))

    batch = executor._gather_batch(max_wait_ms=10, max_batch_size=8)

    assert [request.request_id for request in batch] == [1, 2]
    GpuExecutor._instance = None
