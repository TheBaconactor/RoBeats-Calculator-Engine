import queue

from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequest, GpuRequestType


def test_gpu_executor_dispatch_table_has_skyline_fg_handler():
    executor = GpuExecutor()

    handler = executor._dispatch[GpuRequestType.SKYLINE_FG_FUSED_SOLVE_WITH_BREAKPOINTS]

    assert callable(handler)
    assert handler.__name__ == "_execute_SKYLINE_FG_fused_solve_with_breakpoints"


def test_gpu_executor_pop_queue_request_stamps_dequeue_time():
    executor = GpuExecutor()
    executor._in_process_queues = True
    executor._request_queue = queue.Queue()
    request = GpuRequest(
        request_type=GpuRequestType.LOAD_REF_ARRAYS,
        request_id=123,
        worker_id=0,
        payload={},
    )
    executor._request_queue.put(request)

    popped = executor._pop_queue_request(timeout=0.01)

    assert popped is request
    assert int(popped.dequeue_perf_ns) > 0
