from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequest, GpuRequestType, GpuResponse


def _mk_executor() -> GpuExecutor:
    GpuExecutor._instance = None
    ex = GpuExecutor()
    ex._in_process_queues = True
    return ex


def test_fused_requests_route_through_bounded_batch_coalescer() -> None:
    ex = _mk_executor()
    captured: list[GpuRequest] = []

    def _fake_batch(reqs):
        captured.extend(reqs)
        return [
            GpuResponse(
                request_id=int(req.request_id),
                success=True,
                result=[{"rid": int(req.request_id)}],
            )
            for req in reqs
        ]

    ex._coalesce_fg_solve_with_breakpoints_batch_requests = _fake_batch
    ex._execute_request = lambda req: GpuResponse(request_id=int(req.request_id), success=True, result={"fallback": True})

    reqs = [
        GpuRequest(
            request_type=GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
            request_id=101 + i,
            worker_id=7,
            payload={"payload_index": i},
        )
        for i in range(3)
    ]
    out = ex._coalesce_ga_fg_fused_requests(reqs)

    assert len(captured) == 3
    for i, synthetic in enumerate(captured):
        assert synthetic.request_type == GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH
        assert int(synthetic.request_id) == 101 + i
        assert isinstance(synthetic.payload.get("payloads"), list)
        assert len(synthetic.payload["payloads"]) == 1

    assert [r.result for r in out] == [{"rid": 101}, {"rid": 102}, {"rid": 103}]


def test_fused_requests_fallback_for_invalid_payload() -> None:
    ex = _mk_executor()
    fallback_ids: list[int] = []

    def _fake_batch(reqs):
        return [
            GpuResponse(
                request_id=int(req.request_id),
                success=True,
                result=[{"rid": int(req.request_id)}],
            )
            for req in reqs
        ]

    def _fake_execute(req):
        fallback_ids.append(int(req.request_id))
        return GpuResponse(request_id=int(req.request_id), success=True, result={"fallback": int(req.request_id)})

    ex._coalesce_fg_solve_with_breakpoints_batch_requests = _fake_batch
    ex._execute_request = _fake_execute

    reqs = [
        GpuRequest(
            request_type=GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
            request_id=201,
            worker_id=9,
            payload={"ok": 1},
        ),
        GpuRequest(
            request_type=GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
            request_id=202,
            worker_id=9,
            payload=None,
        ),
    ]

    out = ex._coalesce_ga_fg_fused_requests(reqs)
    assert [r.result for r in out] == [{"rid": 201}, {"fallback": 202}]
    assert fallback_ids == [202]
