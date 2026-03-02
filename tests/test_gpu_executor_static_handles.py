import queue
import threading


def _start_request_responder(request_q: queue.Queue, response_q: queue.Queue, *, scripted_responses=None):
    """
    Start a lightweight in-process responder that mimics the GPU executor response loop.

    This lets us test worker-mode IPC payload shaping without requiring Taichi/GPU.
    """
    from gear_optimizer.solver.gpu_executor import GpuResponse

    captured = []
    stop_sentinel = object()

    # scripted_responses: optional callable(req, captured_so_far) -> GpuResponse
    def _run():
        while True:
            req = request_q.get()
            if req is stop_sentinel:
                return
            captured.append(req)
            if callable(scripted_responses):
                resp = scripted_responses(req, list(captured))
                response_q.put(resp)
                continue
            n = 0
            try:
                gs = (req.payload or {}).get("genome_stats_list")
                n = int(len(gs)) if gs is not None else 0
            except Exception:
                n = 0
            response_q.put(GpuResponse(request_id=req.request_id, success=True, result=[(0, 0, 0, 0, 0, 0, 0)] * n))

    t = threading.Thread(target=_run, name="GpuExecutorTestResponder", daemon=True)
    t.start()

    def _stop():
        request_q.put(stop_sentinel)
        t.join(timeout=2.0)

    return captured, _stop


def test_submit_gpu_solve_genomes_uses_static_handle_after_first_send():
    import numpy as np

    from gear_optimizer.solver.gpu_executor import clear_gpu_worker_mode, set_gpu_worker_mode, submit_gpu_solve_genomes

    req_q: queue.Queue = queue.Queue()
    resp_q: queue.Queue = queue.Queue()
    set_gpu_worker_mode(7, req_q, resp_q)
    captured, stop = _start_request_responder(req_q, resp_q)

    try:
        genome_stats = np.zeros((1, 7), dtype=np.int16)
        calc_song = {"song_data": {"timestamps": [0.0, 1.0]}, "metadata": {"Song Name": "X"}}
        ref_arrays = {"Perfect Points": [0.0] * 161}

        submit_gpu_solve_genomes(
            genome_stats,
            calc_song,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            ref_arrays,
            total_budget=10,
            gem_scale_fever=3,
            song_slot=0,
            timeout=2.0,
        )
        submit_gpu_solve_genomes(
            genome_stats,
            calc_song,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            ref_arrays,
            total_budget=10,
            gem_scale_fever=3,
            song_slot=0,
            timeout=2.0,
        )

        assert len(captured) == 2

        p0 = dict(captured[0].payload or {})
        p1 = dict(captured[1].payload or {})

        assert p0.get("solve_static_inline") is True
        assert p0.get("solve_static_handle") is not None
        assert "timeline_grid" in p0
        assert "ref_arrays" in p0

        assert p1.get("solve_static_inline") is False
        assert p1.get("solve_static_handle") == p0.get("solve_static_handle")
        assert "timeline_grid" not in p1
        assert "ref_arrays" not in p1
    finally:
        stop()
        clear_gpu_worker_mode()


def test_submit_gpu_solve_genomes_retries_on_unknown_static_handle():
    import numpy as np

    from gear_optimizer.solver.gpu_executor import clear_gpu_worker_mode, set_gpu_worker_mode, submit_gpu_solve_genomes
    from gear_optimizer.solver.gpu_executor import GpuResponse

    req_q: queue.Queue = queue.Queue()
    resp_q: queue.Queue = queue.Queue()
    set_gpu_worker_mode(3, req_q, resp_q)

    def scripted(req, captured_so_far):
        payload = req.payload or {}
        n = 0
        try:
            gs = payload.get("genome_stats_list")
            n = int(len(gs)) if gs is not None else 0
        except Exception:
            n = 0
        if payload.get("solve_static_inline") is False:
            return GpuResponse(
                request_id=req.request_id,
                success=False,
                error=f"Unknown solve static handle={payload.get('solve_static_handle')} for worker_id=3",
            )
        return GpuResponse(request_id=req.request_id, success=True, result=[(0, 0, 0, 0, 0, 0, 0)] * n)

    captured, stop = _start_request_responder(req_q, resp_q, scripted_responses=scripted)

    try:
        genome_stats = np.zeros((1, 7), dtype=np.int16)
        calc_song = {"song_data": {"timestamps": [0.0, 1.0]}, "metadata": {"Song Name": "Y"}}
        ref_arrays = {"Perfect Points": [0.0] * 161}

        submit_gpu_solve_genomes(
            genome_stats,
            calc_song,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            ref_arrays,
            total_budget=10,
            gem_scale_fever=3,
            song_slot=0,
            timeout=2.0,
        )
        submit_gpu_solve_genomes(
            genome_stats,
            calc_song,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            ref_arrays,
            total_budget=10,
            gem_scale_fever=3,
            song_slot=0,
            timeout=2.0,
        )

        assert len(captured) == 3
        assert (captured[0].payload or {}).get("solve_static_inline") is True
        assert (captured[1].payload or {}).get("solve_static_inline") is False
        assert (captured[2].payload or {}).get("solve_static_inline") is True
    finally:
        stop()
        clear_gpu_worker_mode()


def test_executor_resolve_solve_payload_caches_static_parts():
    from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequest, GpuRequestType

    GpuExecutor._instance = None
    ex = GpuExecutor()

    req_inline = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_PARALLEL,
        request_id=1,
        worker_id=11,
        payload={
            "solve_static_handle": 123,
            "solve_static_inline": True,
            "timeline_grid": {"song_data": {"timestamps": [0.0, 1.0]}, "metadata": {}},
            "ref_arrays": {"Perfect Points": [0.0] * 161},
        },
    )
    resolved, err = ex._resolve_solve_payload(req_inline)
    assert err is None
    assert "timeline_grid" in resolved
    assert "ref_arrays" in resolved

    req_handle = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_PARALLEL,
        request_id=2,
        worker_id=11,
        payload={
            "solve_static_handle": 123,
            "solve_static_inline": False,
        },
    )
    resolved2, err2 = ex._resolve_solve_payload(req_handle)
    assert err2 is None
    assert resolved2.get("timeline_grid") == resolved.get("timeline_grid")
    assert resolved2.get("ref_arrays") == resolved.get("ref_arrays")
