from gear_optimizer.solver.gpu_executor_fg import (
    build_merged_fg_task_kwargs,
    coalesce_fg_task_requests,
    extract_fg_task_only_request,
    fg_task_only_group_key,
    iter_fg_task_chunks,
    load_fg_task_budget,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


def _req(req_id: int = 1, *, payload: dict | None = None) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        request_id=int(req_id),
        worker_id=1,
        payload=payload or {},
    )


def _args() -> tuple[object, object, object, int, float, object, object]:
    return (object(), object(), object(), 1, 12.5, object(), object())


def test_load_fg_task_budget_prefers_explicit_env_and_clamps_negative():
    assert load_fg_task_budget(
        in_process_queues=True,
        env_get_fn=lambda name, default=None: "33" if name == "FG_TASK_BUDGET" else default,
        env_flag_fn=lambda _name: False,
    ) == 33

    assert load_fg_task_budget(
        in_process_queues=True,
        env_get_fn=lambda name, default=None: "-4" if name == "FG_TASK_BUDGET" else default,
        env_flag_fn=lambda _name: False,
    ) == 0


def test_load_fg_task_budget_defaults_to_safe_inprocess_chunking():
    assert load_fg_task_budget(
        in_process_queues=True,
        env_get_fn=lambda _name, default=None: default,
        env_flag_fn=lambda _name: False,
    ) == 256
    assert load_fg_task_budget(
        in_process_queues=False,
        env_get_fn=lambda _name, default=None: default,
        env_flag_fn=lambda name: name == "INFLIGHT_V4",
    ) == 256
    assert load_fg_task_budget(
        in_process_queues=False,
        env_get_fn=lambda _name, default=None: default,
        env_flag_fn=lambda _name: False,
    ) == 0


def test_extract_fg_task_only_request_accepts_only_non_barrier_task_payloads():
    req = _req()
    payload = {
        "args": _args(),
        "kwargs": {"fg_tasks": [{"a": 1}], "upload_genome_stats": False},
    }

    extracted = extract_fg_task_only_request(req, payload)

    assert extracted is not None
    assert extracted.request is req
    assert extracted.args == tuple(payload["args"])
    assert extracted.kwargs == payload["kwargs"]
    assert extracted.kwargs is not payload["kwargs"]
    assert extracted.fg_tasks == [{"a": 1}]

    assert extract_fg_task_only_request(req, {"args": _args(), "kwargs": {"fg_tasks": []}}) is None
    assert (
        extract_fg_task_only_request(
            req,
            {"args": _args(), "kwargs": {"fg_tasks": [{"a": 1}], "fg_download_after": True}},
        )
        is None
    )
    assert extract_fg_task_only_request(req, {"args": (1, 2), "kwargs": {"fg_tasks": [{"a": 1}]}}) is None


def test_fg_task_only_group_key_tracks_shared_inputs_and_knobs():
    args = _args()
    kwargs = {
        "fg_tasks": [{"a": 1}],
        "n_sections": 4,
        "song_slot": 2,
        "total_budget": 91,
        "gem_scale_fever": 5,
        "is_p_ft": 1,
    }

    key_a = fg_task_only_group_key(args, dict(kwargs))
    key_b = fg_task_only_group_key(args, dict(kwargs))
    key_c = fg_task_only_group_key(args, {**kwargs, "song_slot": 3})
    key_prebuild = fg_task_only_group_key(args, {**kwargs, "prebuild_only": True})

    assert key_a is not None
    assert key_a == key_b
    assert key_a != key_c
    assert key_a != key_prebuild
    assert fg_task_only_group_key((1, 2), kwargs) is None


def test_build_merged_fg_task_kwargs_sets_accumulate_raw_and_strips_request_only_keys():
    merged = build_merged_fg_task_kwargs(
        {
            "fg_tasks": [{"a": 1}],
            "fg_reset_before": True,
            "fg_download_after": True,
            "fg_download_topk": 12,
            "fg_download_base_scores": True,
            "fg_download_keep_mask": True,
            "n_genomes_override": 99,
            "song_slot": 7,
        },
        upload_genome_stats=False,
    )

    assert merged["accumulate_global"] is True
    assert merged["return_raw"] is True
    assert merged["upload_genome_stats"] is False
    assert merged["song_slot"] == 7
    assert "fg_tasks" not in merged
    assert "fg_reset_before" not in merged
    assert "fg_download_after" not in merged
    assert "fg_download_topk" not in merged
    assert "fg_download_base_scores" not in merged
    assert "fg_download_keep_mask" not in merged
    assert "n_genomes_override" not in merged


def test_iter_fg_task_chunks_respects_zero_and_positive_budget():
    tasks = [{"i": i} for i in range(5)]

    assert iter_fg_task_chunks(tasks, 0) == [tasks]
    assert iter_fg_task_chunks(tasks, 2) == [tasks[:2], tasks[2:4], tasks[4:]]


def test_coalesce_fg_task_requests_merges_contiguous_task_only_segment():
    args = _args()
    reqs = [
        _req(1, payload={"args": args, "kwargs": {"fg_tasks": [{"i": 1}], "upload_genome_stats": True}}),
        _req(2, payload={"args": args, "kwargs": {"fg_tasks": [{"i": 2}, {"i": 3}], "upload_genome_stats": False}}),
    ]
    solved_chunks = []
    recorded_batches = []
    recorded_packs = []

    responses = coalesce_fg_task_requests(
        reqs,
        in_process_queues=False,
        execute_request=lambda req: (_ for _ in ()).throw(AssertionError(f"unexpected direct request {req.request_id}")),
        payload_dict_fn=lambda req: req.payload,
        solve_force_greats_finder_gpu_tasks_fn=lambda *args, **kwargs: solved_chunks.append(kwargs),
        record_fg_tasks_batch=recorded_batches.append,
        record_pack=lambda request_type, dt: recorded_packs.append((request_type, dt)),
        perf_counter_fn=iter([10.0, 10.25]).__next__,
        env_get_fn=lambda name, default=None: "2" if name == "FG_TASK_BUDGET" else default,
    )

    assert [resp.request_id for resp in responses] == [1, 2]
    assert all(resp.success for resp in responses)
    assert [chunk["fg_tasks"] for chunk in solved_chunks] == [[{"i": 1}, {"i": 2}], [{"i": 3}]]
    assert [chunk["upload_genome_stats"] for chunk in solved_chunks] == [True, False]
    assert recorded_batches == [1, 2]
    assert recorded_packs == [(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, 0.25)]


def test_coalesce_fg_task_requests_flushes_at_barriers_and_preserves_order():
    args = _args()
    reqs = [
        _req(1, payload={"args": args, "kwargs": {"fg_tasks": [{"i": 1}]}}),
        _req(2, payload={"args": args, "kwargs": {"fg_tasks": [{"i": 2}]}}),
        _req(3, payload={"args": args, "kwargs": {"fg_tasks": [{"i": 3}], "fg_download_after": True}}),
        _req(4, payload={"args": args, "kwargs": {"fg_tasks": [{"i": 4}]}}),
        _req(5, payload={"args": args, "kwargs": {"fg_tasks": [{"i": 5}]}}),
    ]
    solved_batches = []
    direct_requests = []

    responses = coalesce_fg_task_requests(
        reqs,
        in_process_queues=False,
        execute_request=lambda req: direct_requests.append(req.request_id)
        or GpuResponse(request_id=req.request_id, success=True, result=f"direct-{req.request_id}"),
        payload_dict_fn=lambda req: req.payload,
        solve_force_greats_finder_gpu_tasks_fn=lambda *args, **kwargs: solved_batches.append(list(kwargs["fg_tasks"])),
        record_fg_tasks_batch=lambda _count: None,
        record_pack=lambda _request_type, _dt: None,
        perf_counter_fn=iter([1.0, 1.1, 2.0, 2.1]).__next__,
        env_get_fn=lambda _name, default=None: default,
    )

    assert [resp.request_id for resp in responses] == [1, 2, 3, 4, 5]
    assert [resp.result for resp in responses] == [None, None, "direct-3", None, None]
    assert direct_requests == [3]
    assert solved_batches == [[{"i": 1}, {"i": 2}], [{"i": 4}, {"i": 5}]]
