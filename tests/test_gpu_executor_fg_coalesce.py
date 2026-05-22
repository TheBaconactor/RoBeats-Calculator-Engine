import numpy as np

from gear_optimizer.solver.gpu_executor_fg import (
    FgBreakpointCoalesceLimits,
    build_fg_breakpoint_split_requests,
    build_fg_breakpoint_group_bundle,
    coalesce_fg_solve_with_breakpoints_batch_requests,
    fg_breakpoint_payload_pair_count,
    load_fg_breakpoint_coalesce_limits,
    merge_fg_breakpoint_split_results,
    plan_fg_breakpoint_coalescing,
    split_fg_breakpoint_group_result,
    split_fg_breakpoint_payloads_for_coalesce,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


def _req(req_id: int, payload) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
        request_id=int(req_id),
        worker_id=1,
        payload=payload,
    )


def test_load_fg_breakpoint_coalesce_limits_clamps_values():
    values = {
        "FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS": "999",
        "FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAIRS": "-5",
    }

    limits = load_fg_breakpoint_coalesce_limits(env_get_fn=lambda key, default: values.get(key, default))

    assert limits == FgBreakpointCoalesceLimits(max_payloads=512, max_pairs=0)


def test_load_fg_breakpoint_coalesce_limits_uses_defaults_for_invalid_values():
    limits = load_fg_breakpoint_coalesce_limits(env_get_fn=lambda _key, _default: "not-an-int")

    assert limits == FgBreakpointCoalesceLimits(max_payloads=1, max_pairs=256)


def test_fg_breakpoint_payload_pair_count_handles_arrays_lists_and_bad_values():
    payloads = [
        {"ftff_pairs": np.zeros((3, 2), dtype=np.int32)},
        {"ftff_pairs": [[0, 0], [1, 1]]},
        {"ftff_pairs": object()},
        {},
    ]

    assert fg_breakpoint_payload_pair_count(payloads, max_pairs=20) == 5
    assert fg_breakpoint_payload_pair_count(payloads, max_pairs=0) == 0


def test_split_fg_breakpoint_payloads_for_coalesce_splits_by_payload_cap():
    payloads = [{"payload_idx": i} for i in range(5)]

    chunks = split_fg_breakpoint_payloads_for_coalesce(
        payloads,
        limits=FgBreakpointCoalesceLimits(max_payloads=2, max_pairs=0),
    )

    assert [[p["payload_idx"] for p in chunk] for chunk in chunks] == [[0, 1], [2, 3], [4]]


def test_split_fg_breakpoint_payloads_for_coalesce_splits_by_pair_cap():
    payloads = [
        {"ftff_pairs": [[0, 0] for _ in range(12)]},
        {"ftff_pairs": [[1, 1] for _ in range(12)]},
        {"ftff_pairs": [[2, 2] for _ in range(4)]},
    ]

    chunks = split_fg_breakpoint_payloads_for_coalesce(
        payloads,
        limits=FgBreakpointCoalesceLimits(max_payloads=16, max_pairs=20),
    )

    assert [len(chunk) for chunk in chunks] == [1, 2]
    assert [fg_breakpoint_payload_pair_count(chunk, max_pairs=20) for chunk in chunks] == [12, 16]


def test_plan_fg_breakpoint_coalescing_marks_invalid_requests():
    requests = [
        _req(1, {}),
        _req(2, {"payloads": [object()]}),
        _req(3, {"payloads": [{"ok": True}]}),
    ]

    plan = plan_fg_breakpoint_coalescing(
        requests,
        payload_dict_fn=lambda req: dict(req.payload or {}),
        limits=FgBreakpointCoalesceLimits(max_payloads=8, max_pairs=0),
    )

    assert [(req.request_id, reason) for req, reason in plan.invalid] == [
        (1, "missing/empty payloads list"),
        (2, "payload list contains non-dict item"),
    ]
    assert [[entry.request.request_id for entry in group] for group in plan.groups] == [[3]]


def test_plan_fg_breakpoint_coalescing_separates_oversized_requests():
    requests = [
        _req(1, {"payloads": [{"payload_idx": i} for i in range(5)]}),
        _req(2, {"payloads": [{"ok": True}]}),
    ]

    plan = plan_fg_breakpoint_coalescing(
        requests,
        payload_dict_fn=lambda req: dict(req.payload or {}),
        limits=FgBreakpointCoalesceLimits(max_payloads=2, max_pairs=0),
    )

    assert [item.entry.request.request_id for item in plan.oversized] == [1]
    assert [[p["payload_idx"] for p in chunk] for chunk in plan.oversized[0].chunks] == [[0, 1], [2, 3], [4]]
    assert [[entry.request.request_id for entry in group] for group in plan.groups] == [[2]]


def test_plan_fg_breakpoint_coalescing_groups_until_limits():
    requests = [
        _req(1, {"payloads": [{"ftff_pairs": [[0, 0] for _ in range(4)]}]}),
        _req(2, {"payloads": [{"ftff_pairs": [[1, 1] for _ in range(4)]}]}),
        _req(3, {"payloads": [{"ftff_pairs": [[2, 2] for _ in range(4)]}]}),
    ]

    plan = plan_fg_breakpoint_coalescing(
        requests,
        payload_dict_fn=lambda req: dict(req.payload or {}),
        limits=FgBreakpointCoalesceLimits(max_payloads=8, max_pairs=8),
    )

    assert [[entry.request.request_id for entry in group] for group in plan.groups] == [[1, 2], [3]]


def test_plan_fg_breakpoint_coalescing_keeps_single_large_pair_payload_direct():
    requests = [
        _req(1, {"payloads": [{"ftff_pairs": [[0, 0] for _ in range(620)]}]}),
        _req(2, {"payloads": [{"ftff_pairs": [[1, 1] for _ in range(4)]}]}),
    ]

    plan = plan_fg_breakpoint_coalescing(
        requests,
        payload_dict_fn=lambda req: dict(req.payload or {}),
        limits=FgBreakpointCoalesceLimits(max_payloads=8, max_pairs=256),
    )

    assert plan.oversized == []
    assert [[entry.request.request_id for entry in group] for group in plan.groups] == [[1], [2]]


def test_build_fg_breakpoint_group_bundle_merges_payloads_and_tracks_slices():
    plan = plan_fg_breakpoint_coalescing(
        [
            _req(1, {"payloads": [{"payload_idx": 0}, {"payload_idx": 1}]}),
            _req(2, {"payloads": [{"payload_idx": 2}]}),
        ],
        payload_dict_fn=lambda req: dict(req.payload or {}),
        limits=FgBreakpointCoalesceLimits(max_payloads=8, max_pairs=0),
    )

    bundle = build_fg_breakpoint_group_bundle(plan.groups[0])

    assert bundle.request.request_type == GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH
    assert bundle.request.request_id == -1
    assert bundle.request.payload == {
        "payloads": [{"payload_idx": 0}, {"payload_idx": 1}, {"payload_idx": 2}]
    }
    assert [(req.request_id, start, n) for req, start, n in bundle.slices] == [(1, 0, 2), (2, 2, 1)]
    assert bundle.payload_count == 3


def test_split_fg_breakpoint_group_result_restores_per_request_results():
    plan = plan_fg_breakpoint_coalescing(
        [
            _req(1, {"payloads": [{"payload_idx": 0}, {"payload_idx": 1}]}),
            _req(2, {"payloads": [{"payload_idx": 2}]}),
        ],
        payload_dict_fn=lambda req: dict(req.payload or {}),
        limits=FgBreakpointCoalesceLimits(max_payloads=8, max_pairs=0),
    )
    bundle = build_fg_breakpoint_group_bundle(plan.groups[0])

    responses = split_fg_breakpoint_group_result(bundle, ["r0", "r1", "r2"])

    assert [(resp.request_id, resp.success, resp.result) for resp in responses] == [
        (1, True, ["r0", "r1"]),
        (2, True, ["r2"]),
    ]


def test_split_fg_breakpoint_group_result_rejects_bad_result_shape():
    plan = plan_fg_breakpoint_coalescing(
        [_req(1, {"payloads": [{"payload_idx": 0}]})],
        payload_dict_fn=lambda req: dict(req.payload or {}),
        limits=FgBreakpointCoalesceLimits(max_payloads=8, max_pairs=0),
    )
    bundle = build_fg_breakpoint_group_bundle(plan.groups[0])

    try:
        split_fg_breakpoint_group_result(bundle, object())
    except TypeError as exc:
        assert "non-list" in str(exc)
    else:
        raise AssertionError("expected TypeError")

    try:
        split_fg_breakpoint_group_result(bundle, ["r0", "extra"])
    except RuntimeError as exc:
        assert "length mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_build_fg_breakpoint_split_requests_preserves_original_request_identity():
    plan = plan_fg_breakpoint_coalescing(
        [_req(7, {"payloads": [{"payload_idx": i} for i in range(5)]})],
        payload_dict_fn=lambda req: dict(req.payload or {}),
        limits=FgBreakpointCoalesceLimits(max_payloads=2, max_pairs=0),
    )

    split_requests = build_fg_breakpoint_split_requests(plan.oversized[0])

    assert [item.request.request_id for item in split_requests] == [7, 7, 7]
    assert [item.request.worker_id for item in split_requests] == [1, 1, 1]
    assert [item.expected_results for item in split_requests] == [2, 2, 1]
    assert [item.request.payload["payloads"] for item in split_requests] == [
        [{"payload_idx": 0}, {"payload_idx": 1}],
        [{"payload_idx": 2}, {"payload_idx": 3}],
        [{"payload_idx": 4}],
    ]


def test_merge_fg_breakpoint_split_results_validates_and_flattens_chunks():
    plan = plan_fg_breakpoint_coalescing(
        [_req(7, {"payloads": [{"payload_idx": i} for i in range(3)]})],
        payload_dict_fn=lambda req: dict(req.payload or {}),
        limits=FgBreakpointCoalesceLimits(max_payloads=2, max_pairs=0),
    )
    split_requests = build_fg_breakpoint_split_requests(plan.oversized[0])

    assert merge_fg_breakpoint_split_results(split_requests, [["a", "b"], ["c"]]) == ["a", "b", "c"]

    try:
        merge_fg_breakpoint_split_results(split_requests, [["a", "b"]])
    except RuntimeError as exc:
        assert "chunk count mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    try:
        merge_fg_breakpoint_split_results(split_requests, [["a"], ["c"]])
    except RuntimeError as exc:
        assert "length mismatch" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    try:
        merge_fg_breakpoint_split_results(split_requests, [["a", "b"], object()])
    except TypeError as exc:
        assert "non-list" in str(exc)
    else:
        raise AssertionError("expected TypeError")


def test_coalesce_fg_solve_with_breakpoints_batch_requests_merges_group():
    direct_calls = []
    warnings = []

    responses = coalesce_fg_solve_with_breakpoints_batch_requests(
        [
            _req(1, {"payloads": [{"payload_idx": 0}, {"payload_idx": 1}]}),
            _req(2, {"payloads": [{"payload_idx": 2}]}),
        ],
        in_process_queues=True,
        execute_request=lambda req: direct_calls.append(req.request_id)
        or GpuResponse(request_id=req.request_id, success=True, result=["direct"]),
        execute_batch=lambda req: GpuResponse(
            request_id=req.request_id,
            success=True,
            result=[payload["payload_idx"] for payload in req.payload["payloads"]],
        ),
        payload_dict_fn=lambda req: dict(req.payload or {}),
        warn_fallback_fn=lambda *args, **kwargs: warnings.append((args, kwargs)),
        env_get_fn=lambda key, default: {"FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS": "8"}.get(key, default),
    )

    assert direct_calls == []
    assert warnings == []
    assert [(response.request_id, response.result) for response in responses] == [(1, [0, 1]), (2, [2])]


def test_coalesce_fg_solve_with_breakpoints_batch_requests_falls_back_when_not_inprocess():
    direct_calls = []
    warnings = []

    responses = coalesce_fg_solve_with_breakpoints_batch_requests(
        [_req(5, {"payloads": [{"payload_idx": 0}]})],
        in_process_queues=False,
        execute_request=lambda req: direct_calls.append(req.request_id)
        or GpuResponse(request_id=req.request_id, success=True, result=["direct"]),
        execute_batch=lambda req: GpuResponse(request_id=req.request_id, success=True, result=[]),
        payload_dict_fn=lambda req: dict(req.payload or {}),
        warn_fallback_fn=lambda *args, **kwargs: warnings.append((args, kwargs)),
    )

    assert direct_calls == [5]
    assert responses[0].result == ["direct"]
    assert warnings[0][0][:2] == (
        "gpu_executor.fg_breakpoints_coalesce",
        "coalescing unavailable (not in-process); falling back to per-request execution",
    )


def test_coalesce_fg_solve_with_breakpoints_batch_requests_executes_single_entry_group_direct():
    direct_calls = []

    responses = coalesce_fg_solve_with_breakpoints_batch_requests(
        [_req(5, {"payloads": [{"ftff_pairs": [[0, 0] for _ in range(620)]}]})],
        in_process_queues=True,
        execute_request=lambda req: direct_calls.append(req.request_id)
        or GpuResponse(request_id=req.request_id, success=True, result=["direct"]),
        execute_batch=lambda req: GpuResponse(request_id=req.request_id, success=True, result=[]),
        payload_dict_fn=lambda req: dict(req.payload or {}),
        warn_fallback_fn=lambda *args, **kwargs: None,
    )

    assert direct_calls == [5]
    assert responses[0].result == ["direct"]
