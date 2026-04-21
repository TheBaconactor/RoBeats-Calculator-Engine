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
    executor.clear_abort()
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


def test_execute_gpu_native_ga_run_chunk_aborts_remaining_requests(monkeypatch):
    executor = GpuExecutor()
    executor.clear_abort()
    calls: list[int] = []

    def _fake_single(req: GpuRequest) -> GpuResponse:
        calls.append(int(req.request_id))
        executor.request_abort("hotkey stop")
        return GpuResponse(request_id=int(req.request_id), success=True, result={"rid": int(req.request_id)})

    monkeypatch.setattr(executor, "_execute_gpu_native_ga_run", _fake_single)

    reqs = [
        _req(121, GpuRequestType.GPU_NATIVE_GA_RUN, {"song_slot": 1}),
        _req(122, GpuRequestType.GPU_NATIVE_GA_RUN, {"song_slot": 2}),
        _req(123, GpuRequestType.GPU_NATIVE_GA_RUN, {"song_slot": 3}),
    ]
    out = executor._execute_gpu_native_ga_run_chunk(reqs)
    executor.clear_abort()

    assert calls == [121]
    assert [r.request_id for r in out] == [121, 122, 123]
    assert out[0].success is True
    assert all(r.success is False for r in out[1:])
    assert all("GpuExecutor aborted: hotkey stop" in str(r.error) for r in out[1:])


def test_execute_gpu_native_ga_run_batch_splits_large_chunks(monkeypatch):
    executor = GpuExecutor()
    monkeypatch.setenv("GPU_NATIVE_GA_BATCH_COALESCE_MAX_REQS", "2")
    monkeypatch.setenv("GPU_NATIVE_GA_BATCH_COALESCE_MAX_WORK_UNITS", "1000000")

    seen_chunks: list[list[int]] = []

    def _fake_chunk(reqs):
        chunk_ids = [int(req.request_id) for req in reqs]
        seen_chunks.append(chunk_ids)
        return [
            GpuResponse(request_id=int(req.request_id), success=True, result={"rid": int(req.request_id)})
            for req in reqs
        ]

    monkeypatch.setattr(executor, "_execute_gpu_native_ga_run_chunk", _fake_chunk)

    reqs = [
        _req(111, GpuRequestType.GPU_NATIVE_GA_RUN, {"song_slot": 1}),
        _req(112, GpuRequestType.GPU_NATIVE_GA_RUN, {"song_slot": 2}),
        _req(113, GpuRequestType.GPU_NATIVE_GA_RUN, {"song_slot": 3}),
        _req(114, GpuRequestType.GPU_NATIVE_GA_RUN, {"song_slot": 4}),
        _req(115, GpuRequestType.GPU_NATIVE_GA_RUN, {"song_slot": 5}),
    ]
    out = executor._execute_gpu_native_ga_run_batch(reqs)

    assert seen_chunks == [[111, 112], [113, 114], [115]]
    assert [r.request_id for r in out] == [111, 112, 113, 114, 115]
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


def test_coalesce_fg_breakpoints_splits_oversized_request(monkeypatch):
    executor = GpuExecutor()
    executor._in_process_queues = True
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS", "16")

    seen_chunk_sizes: list[int] = []

    def _fake_batch(req: GpuRequest) -> GpuResponse:
        payloads = (req.payload or {}).get("payloads") or []
        seen_chunk_sizes.append(len(payloads))
        return GpuResponse(
            request_id=int(req.request_id),
            success=True,
            result=[{"chunk": len(seen_chunk_sizes), "idx": i} for i in range(len(payloads))],
        )

    monkeypatch.setattr(executor, "_execute_fg_solve_with_breakpoints_batch", _fake_batch)

    req = _req(
        401,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
        {"payloads": [{"payload_idx": i} for i in range(19)]},
    )
    out = executor._coalesce_fg_solve_with_breakpoints_batch_requests([req])

    assert seen_chunk_sizes == [16, 3]
    assert len(out) == 1
    assert out[0].request_id == 401
    assert out[0].success is True
    assert isinstance(out[0].result, list)
    assert len(out[0].result) == 19


def test_coalesce_fg_breakpoints_splits_when_pairs_exceed_cap(monkeypatch):
    executor = GpuExecutor()
    executor._in_process_queues = True
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS", "16")
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAIRS", "20")

    seen_chunk_shapes: list[tuple[int, int]] = []

    def _fake_batch(req: GpuRequest) -> GpuResponse:
        payloads = (req.payload or {}).get("payloads") or []
        pair_total = sum(len((p or {}).get("ftff_pairs") or []) for p in payloads)
        seen_chunk_shapes.append((len(payloads), int(pair_total)))
        return GpuResponse(
            request_id=int(req.request_id),
            success=True,
            result=[{"pairs": int(pair_total), "idx": i} for i in range(len(payloads))],
        )

    monkeypatch.setattr(executor, "_execute_fg_solve_with_breakpoints_batch", _fake_batch)

    payloads = [
        {"ftff_pairs": [[0, 0] for _ in range(12)]},
        {"ftff_pairs": [[1, 1] for _ in range(12)]},
        {"ftff_pairs": [[2, 2] for _ in range(12)]},
    ]
    req = _req(501, GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH, {"payloads": payloads})
    out = executor._coalesce_fg_solve_with_breakpoints_batch_requests([req])

    assert seen_chunk_shapes == [(1, 12), (1, 12), (1, 12)]
    assert len(out) == 1
    assert out[0].request_id == 501
    assert out[0].success is True
    assert isinstance(out[0].result, list)
    assert len(out[0].result) == 3


def test_coalesce_exact_dp_merges_same_song_context(monkeypatch):
    from gear_optimizer.solver.taichi_gem.force_greats import api as fg_api

    executor = GpuExecutor()
    calc_song = {"metadata": {}, "song_data": {}}
    ref_arrays = {"refs": True}
    calls: list[list[int]] = []

    def _fake_exact_batch(*, stats_list, calc_song, ref_arrays, timing_aware=True, prune=True, song_slot=0):
        rows = list(stats_list or [])
        calls.append([int(row["row"]) for row in rows])
        assert timing_aware is True
        assert prune is True
        assert song_slot == 5
        return [{"row": int(row["row"])} for row in rows]

    monkeypatch.setattr(fg_api, "solve_force_greats_exact_dp_gpu_batch", _fake_exact_batch)

    reqs = [
        _req(
            601,
            GpuRequestType.SOLVE_FORCE_GREATS_EXACT_DP,
            {
                "stats_list": [{"row": 1}],
                "calc_song": calc_song,
                "ref_arrays": ref_arrays,
                "song_slot": 5,
            },
        ),
        _req(
            602,
            GpuRequestType.SOLVE_FORCE_GREATS_EXACT_DP,
            {
                "stats_list": [{"row": 2}, {"row": 3}],
                "calc_song": calc_song,
                "ref_arrays": ref_arrays,
                "song_slot": 5,
            },
        ),
    ]

    out = executor._coalesce_solve_force_greats_exact_dp_requests(reqs)

    assert calls == [[1, 2, 3]]
    assert [r.request_id for r in out] == [601, 602]
    assert [item["row"] for item in out[0].result] == [1]
    assert [item["row"] for item in out[1].result] == [2, 3]
