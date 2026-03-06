import queue
import threading

import numpy as np


def _start_request_responder(request_q: queue.Queue, response_q: queue.Queue, *, scripted_responses=None):
    """
    Start a lightweight in-process responder that mimics the GPU executor response loop.

    This lets us test worker-mode IPC payload shaping without requiring Taichi/GPU.
    """
    from gear_optimizer.solver.gpu_executor import GpuResponse

    captured = []
    stop_sentinel = object()

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
                pop = (req.payload or {}).get("population_indices")
                n = int(len(pop)) if pop is not None else 0
            except Exception:
                n = 0
            response_q.put(GpuResponse(request_id=req.request_id, success=True, result=[(0, 0, 0, 0, 0, 0, 0)] * n))

    t = threading.Thread(target=_run, name="GpuExecutorTestResponder", daemon=True)
    t.start()

    def _stop():
        request_q.put(stop_sentinel)
        t.join(timeout=2.0)

    return captured, _stop


def _submit_registry_request(
    *,
    population_indices,
    item_stats,
    slot_start,
    slot_count,
    base_fixed_stats,
    calc_song,
    ref_arrays,
    timeout=2.0,
):
    from gear_optimizer.solver.gpu_executor import submit_gpu_solve_genomes_from_registry

    return submit_gpu_solve_genomes_from_registry(
        population_indices,
        item_stats,
        slot_start,
        slot_count,
        base_fixed_stats,
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
        timeout=timeout,
    )


def test_submit_gpu_solve_genomes_from_registry_uses_static_handle_after_first_send():
    from gear_optimizer.solver.gpu_executor import clear_gpu_worker_mode, set_gpu_worker_mode

    req_q: queue.Queue = queue.Queue()
    resp_q: queue.Queue = queue.Queue()
    set_gpu_worker_mode(7, req_q, resp_q)
    captured, stop = _start_request_responder(req_q, resp_q)

    try:
        pop_a = np.arange(9, dtype=np.int32).reshape(1, 9)
        pop_b = np.arange(18, dtype=np.int32).reshape(2, 9)
        item_stats = np.arange(40, dtype=np.int16).reshape(4, 10)
        slot_start = np.arange(9, dtype=np.int32)
        slot_count = np.ones(9, dtype=np.int32)
        base_fixed_stats = np.arange(10, dtype=np.int32)
        calc_song = {
            "song_data": {"timestamps": np.array([0.0, 1.0], dtype=np.float32)},
            "metadata": {"Song Name": "registry-static"},
        }
        ref_arrays = {"Perfect Points": [0.0] * 161}

        _submit_registry_request(
            population_indices=pop_a,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats=base_fixed_stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
        )
        _submit_registry_request(
            population_indices=pop_b,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats=base_fixed_stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
        )

        assert len(captured) == 2

        p0 = dict(captured[0].payload or {})
        p1 = dict(captured[1].payload or {})

        assert p0.get("registry_payload_inline") is True
        assert p0.get("registry_payload_handle") is not None
        assert "item_stats" in p0
        assert "slot_start" in p0
        assert "slot_count" in p0
        assert "base_fixed_stats" in p0
        assert "timeline_grid" in p0
        assert "ref_arrays" in p0

        assert p1.get("registry_payload_inline") is False
        assert p1.get("registry_payload_handle") == p0.get("registry_payload_handle")
        assert "item_stats" not in p1
        assert "slot_start" not in p1
        assert "slot_count" not in p1
        assert "base_fixed_stats" not in p1
        assert "timeline_grid" not in p1
        assert "ref_arrays" not in p1
    finally:
        stop()
        clear_gpu_worker_mode()


def test_submit_gpu_solve_genomes_from_registry_retries_on_unknown_static_handle():
    from gear_optimizer.solver.gpu_executor import GpuResponse
    from gear_optimizer.solver.gpu_executor import clear_gpu_worker_mode, set_gpu_worker_mode

    req_q: queue.Queue = queue.Queue()
    resp_q: queue.Queue = queue.Queue()
    set_gpu_worker_mode(3, req_q, resp_q)

    def scripted(req, captured_so_far):
        del captured_so_far
        payload = req.payload or {}
        n = 0
        try:
            pop = payload.get("population_indices")
            n = int(len(pop)) if pop is not None else 0
        except Exception:
            n = 0
        if payload.get("registry_payload_inline") is False:
            return GpuResponse(
                request_id=req.request_id,
                success=False,
                error=f"Unknown registry payload handle={payload.get('registry_payload_handle')} for worker_id=3",
            )
        return GpuResponse(request_id=req.request_id, success=True, result=[(0, 0, 0, 0, 0, 0, 0)] * n)

    captured, stop = _start_request_responder(req_q, resp_q, scripted_responses=scripted)

    try:
        pop = np.arange(9, dtype=np.int32).reshape(1, 9)
        item_stats = np.arange(40, dtype=np.int16).reshape(4, 10)
        slot_start = np.arange(9, dtype=np.int32)
        slot_count = np.ones(9, dtype=np.int32)
        base_fixed_stats = np.arange(10, dtype=np.int32)
        calc_song = {
            "song_data": {"timestamps": np.array([0.0, 1.0], dtype=np.float32)},
            "metadata": {"Song Name": "registry-static"},
        }
        ref_arrays = {"Perfect Points": [0.0] * 161}

        _submit_registry_request(
            population_indices=pop,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats=base_fixed_stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
        )
        _submit_registry_request(
            population_indices=pop,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats=base_fixed_stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
        )

        assert len(captured) == 3
        assert (captured[0].payload or {}).get("registry_payload_inline") is True
        assert (captured[1].payload or {}).get("registry_payload_inline") is False
        assert (captured[2].payload or {}).get("registry_payload_inline") is True
    finally:
        stop()
        clear_gpu_worker_mode()


def test_executor_resolve_registry_payload_caches_static_parts():
    from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequest, GpuRequestType

    GpuExecutor._instance = None
    ex = GpuExecutor()

    req_inline = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=1,
        worker_id=11,
        payload={
            "registry_payload_handle": 123,
            "registry_payload_inline": True,
            "item_stats": np.arange(40, dtype=np.int16).reshape(4, 10),
            "slot_start": np.arange(9, dtype=np.int32),
            "slot_count": np.ones(9, dtype=np.int32),
            "base_fixed_stats": np.arange(10, dtype=np.int32),
            "timeline_grid": {"song_data": {"timestamps": [0.0, 1.0]}, "metadata": {}},
            "ref_arrays": {"Perfect Points": [0.0] * 161},
        },
    )
    resolved, err = ex._resolve_registry_payload(req_inline)
    assert err is None
    assert "item_stats" in resolved
    assert "timeline_grid" in resolved
    assert "ref_arrays" in resolved

    req_handle = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=2,
        worker_id=11,
        payload={
            "registry_payload_handle": 123,
            "registry_payload_inline": False,
        },
    )
    resolved2, err2 = ex._resolve_registry_payload(req_handle)
    assert err2 is None
    assert np.array_equal(resolved2.get("item_stats"), resolved.get("item_stats"))
    assert np.array_equal(resolved2.get("slot_start"), resolved.get("slot_start"))
    assert np.array_equal(resolved2.get("slot_count"), resolved.get("slot_count"))
    assert np.array_equal(resolved2.get("base_fixed_stats"), resolved.get("base_fixed_stats"))
    assert resolved2.get("timeline_grid") == resolved.get("timeline_grid")
    assert resolved2.get("ref_arrays") == resolved.get("ref_arrays")
