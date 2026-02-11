from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequest, GpuRequestType, GpuResponse


def _req(req_id: int, req_type: GpuRequestType, payload: dict | None = None) -> GpuRequest:
    return GpuRequest(
        request_type=req_type,
        request_id=int(req_id),
        worker_id=1,
        payload=dict(payload or {}),
    )


def test_execute_gpu_native_ga_run_batch_preserves_order(monkeypatch):
    executor = GpuExecutor()
    calls: list[int] = []

    def _fake_single(req: GpuRequest) -> GpuResponse:
        calls.append(int(req.request_id))
        return GpuResponse(request_id=int(req.request_id), success=True, result={"rid": int(req.request_id)})

    monkeypatch.setattr(executor, "_execute_gpu_native_ga_run", _fake_single)

    reqs = [
        _req(101, GpuRequestType.GPU_NATIVE_GA_RUN, {"song_slot": 1}),
        _req(102, GpuRequestType.GPU_NATIVE_GA_RUN, {"song_slot": 2}),
        _req(103, GpuRequestType.GPU_NATIVE_GA_RUN, {"song_slot": 3}),
    ]
    out = executor._execute_gpu_native_ga_run_batch(reqs)

    assert calls == [101, 102, 103]
    assert [r.request_id for r in out] == [101, 102, 103]
    assert all(r.success for r in out)


def test_coalesce_ga_fg_fused_requests_uses_batch_handler(monkeypatch):
    executor = GpuExecutor()
    executor._in_process_queues = True

    reqs = [
        _req(201, GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS, {"n_sections": 1, "ftff_pairs": [[0, 0]]}),
        _req(202, GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS, {"n_sections": 1, "ftff_pairs": [[1, 1]]}),
    ]

    seen = {"batch_payload_count": 0}

    def _fake_batch(req: GpuRequest) -> GpuResponse:
        payloads = (req.payload or {}).get("payloads") or []
        seen["batch_payload_count"] = len(payloads)
        return GpuResponse(
            request_id=req.request_id,
            success=True,
            result=[{"final_score": 1001}, {"final_score": 1002}],
        )

    monkeypatch.setattr(executor, "_execute_fg_solve_with_breakpoints_batch", _fake_batch)

    out = executor._coalesce_ga_fg_fused_requests(reqs)

    assert seen["batch_payload_count"] == 2
    assert [r.request_id for r in out] == [201, 202]
    assert [r.result["final_score"] for r in out] == [1001, 1002]


def test_coalesce_ga_fg_fused_requests_falls_back_when_not_inprocess(monkeypatch):
    executor = GpuExecutor()
    executor._in_process_queues = False

    reqs = [
        _req(301, GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS, {"n_sections": 1}),
        _req(302, GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS, {"n_sections": 1}),
    ]

    calls: list[int] = []

    def _fake_exec(req: GpuRequest) -> GpuResponse:
        calls.append(int(req.request_id))
        return GpuResponse(request_id=int(req.request_id), success=True, result={"fallback": True})

    monkeypatch.setattr(executor, "_execute_request", _fake_exec)

    out = executor._coalesce_ga_fg_fused_requests(reqs)

    assert calls == [301, 302]
    assert [r.request_id for r in out] == [301, 302]
