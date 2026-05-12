from gear_optimizer.solver.gpu_executor_profile import (
    build_exec_breakdown_summary,
    build_executor_idle_summary,
    build_executor_profile_stats,
    build_executor_stats,
    build_idle_transition_summary,
    build_request_latency_summary,
    compute_exec_breakdown,
    compute_request_latency_window,
    exec_breakdown_enabled,
    exec_breakdown_summary_log_message,
    executor_profile_log_message,
    fg_tasks_per_sec_log_message,
    gpu_profiler_snapshot,
    idle_transition_summary_log_message,
    profile_events_output_enabled,
    record_exec_breakdown_stats,
    record_fg_task_batch_stats,
    record_pack_stats,
    record_request_latency_stats,
    request_latency_summary_log_message,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def test_compute_exec_breakdown_attributes_profiler_deltas_and_host_residual():
    breakdown = compute_exec_breakdown(
        exec_wall_sec=10.0,
        prof_before=(1.0, 2.0, 3.0),
        prof_after=(3.5, 2.5, 4.0),
    )

    assert breakdown is not None
    assert breakdown.gpu_kernel_sec == 2.5
    assert breakdown.gpu_upload_sec == 0.5
    assert breakdown.gpu_download_sec == 1.0
    assert breakdown.host_sec == 6.0


def test_compute_exec_breakdown_clamps_negative_deltas_and_host():
    breakdown = compute_exec_breakdown(
        exec_wall_sec=1.0,
        prof_before=(5.0, 5.0, 5.0),
        prof_after=(4.0, 4.0, 8.0),
    )

    assert breakdown is not None
    assert breakdown.gpu_kernel_sec == 0.0
    assert breakdown.gpu_upload_sec == 0.0
    assert breakdown.gpu_download_sec == 3.0
    assert breakdown.host_sec == 0.0
    assert compute_exec_breakdown(exec_wall_sec=0.0, prof_before=None, prof_after=None) is None


def test_exec_breakdown_enabled_uses_profile_gpu_profiler_or_env_flag():
    assert exec_breakdown_enabled(
        profile_enabled=True,
        gpu_profiler_enabled=False,
        env_flag_fn=lambda _key, _default: False,
    )
    assert exec_breakdown_enabled(
        profile_enabled=False,
        gpu_profiler_enabled=True,
        env_flag_fn=lambda _key, _default: False,
    )
    assert exec_breakdown_enabled(
        profile_enabled=False,
        gpu_profiler_enabled=False,
        env_flag_fn=lambda _key, _default: True,
    )
    assert not exec_breakdown_enabled(
        profile_enabled=False,
        gpu_profiler_enabled=False,
        env_flag_fn=lambda _key, _default: False,
    )


def test_profile_events_output_enabled_checks_metafinder_or_generic_path():
    assert profile_events_output_enabled(
        env_get_fn=lambda key: {"METAFINDER_PROFILE_EVENTS_PATH": "events.jsonl"}.get(key, "")
    )
    assert profile_events_output_enabled(env_get_fn=lambda key: {"PROFILE_EVENTS_PATH": "events.jsonl"}.get(key, ""))
    assert not profile_events_output_enabled(env_get_fn=lambda _key: " ")
    assert not profile_events_output_enabled(
        env_get_fn=lambda _key: (_ for _ in ()).throw(TypeError("bad env"))
    )


def test_record_exec_breakdown_stats_accumulates_breakdown_buckets():
    from collections import defaultdict

    host = defaultdict(float)
    kernel = defaultdict(float)
    upload = defaultdict(float)
    download = defaultdict(float)
    breakdown = compute_exec_breakdown(
        exec_wall_sec=2.0,
        prof_before=(1.0, 1.0, 1.0),
        prof_after=(1.5, 1.25, 1.25),
    )
    assert breakdown is not None

    assert record_exec_breakdown_stats(
        GpuRequestType.GPU_NATIVE_GA_RUN,
        breakdown,
        req_type_host_sec=host,
        req_type_gpu_kernel_sec=kernel,
        req_type_gpu_upload_sec=upload,
        req_type_gpu_download_sec=download,
    )

    assert host[GpuRequestType.GPU_NATIVE_GA_RUN] == 1.0
    assert kernel[GpuRequestType.GPU_NATIVE_GA_RUN] == 0.5
    assert upload[GpuRequestType.GPU_NATIVE_GA_RUN] == 0.25
    assert download[GpuRequestType.GPU_NATIVE_GA_RUN] == 0.25


def test_record_fg_task_batch_stats_accumulates_counts_and_histogram():
    from collections import defaultdict

    hist = defaultdict(int)
    stats = record_fg_task_batch_stats(
        7,
        batches=2,
        total=10,
        max_tasks=5,
        batch_hist=hist,
    )

    assert stats.batches == 3
    assert stats.total == 17
    assert stats.max_tasks == 7
    assert hist[7] == 1


def test_record_fg_task_batch_stats_ignores_empty_or_invalid_batches():
    from collections import defaultdict

    hist = defaultdict(int)

    zero_stats = record_fg_task_batch_stats(
        0,
        batches=2,
        total=10,
        max_tasks=5,
        batch_hist=hist,
    )
    invalid_stats = record_fg_task_batch_stats(
        "bad",
        batches=2,
        total=10,
        max_tasks=5,
        batch_hist=hist,
    )

    assert zero_stats.batches == 2
    assert zero_stats.total == 10
    assert zero_stats.max_tasks == 5
    assert invalid_stats == zero_stats
    assert dict(hist) == {}


def test_record_pack_stats_accumulates_total_and_type_bucket():
    from collections import defaultdict

    buckets = defaultdict(float)
    total = record_pack_stats(
        GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        0.125,
        pack_sec=1.0,
        req_type_pack_sec=buckets,
    )

    assert total == 1.125
    assert buckets[GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY] == 0.125


def test_record_pack_stats_ignores_invalid_or_empty_duration():
    from collections import defaultdict

    buckets = defaultdict(float)

    assert (
        record_pack_stats(
            GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
            0.0,
            pack_sec=1.0,
            req_type_pack_sec=buckets,
        )
        == 1.0
    )
    assert (
        record_pack_stats(
            GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
            "bad",
            pack_sec=1.0,
            req_type_pack_sec=buckets,
        )
        == 1.0
    )
    assert dict(buckets) == {}


def test_gpu_profiler_snapshot_reads_profiler_totals_when_enabled():
    class _Profiler:
        @staticmethod
        def summary():
            return {
                "total_kernel_sec": "1.25",
                "total_upload_sec": 0.5,
                "total_download_sec": None,
            }

    assert gpu_profiler_snapshot(enabled=True, get_gpu_profiler_fn=lambda: _Profiler()) == (1.25, 0.5, 0.0)


def test_gpu_profiler_snapshot_returns_zero_when_disabled_or_unavailable():
    assert gpu_profiler_snapshot(enabled=False, get_gpu_profiler_fn=lambda: object()) == (0.0, 0.0, 0.0)
    assert (
        gpu_profiler_snapshot(
            enabled=True,
            get_gpu_profiler_fn=lambda: (_ for _ in ()).throw(RuntimeError("missing")),
        )
        == (0.0, 0.0, 0.0)
    )


def test_compute_request_latency_window_uses_dequeue_and_exec_boundaries():
    request = GpuRequest(
        request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
        request_id=1,
        worker_id=0,
        payload={},
        submit_perf_ns=1_000,
        dequeue_perf_ns=3_000,
    )

    latency = compute_request_latency_window(request, exec_start_ns=5_000, exec_end_ns=9_000)

    assert latency is not None
    assert latency.request_type == GpuRequestType.GPU_NATIVE_GA_RUN
    assert latency.queue_sec == 2_000 / 1e9
    assert latency.in_exec_sec == 2_000 / 1e9
    assert latency.total_sec == 8_000 / 1e9


def test_compute_request_latency_window_clamps_missing_or_out_of_order_times():
    missing_dequeue = GpuRequest(
        request_type=GpuRequestType.LOAD_REF_ARRAYS,
        request_id=2,
        worker_id=0,
        payload={},
        submit_perf_ns=1_000,
        dequeue_perf_ns=0,
    )

    latency = compute_request_latency_window(missing_dequeue, exec_start_ns=5_000, exec_end_ns=4_000)

    assert latency is not None
    assert latency.queue_sec == 4_000 / 1e9
    assert latency.in_exec_sec == 0.0
    assert latency.total_sec == 4_000 / 1e9
    assert compute_request_latency_window(missing_dequeue, exec_start_ns=5_000, exec_end_ns=0) is None


def test_record_request_latency_stats_updates_totals_and_appends_samples():
    latency = compute_request_latency_window(
        GpuRequest(
            request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
            request_id=3,
            worker_id=0,
            payload={},
            submit_perf_ns=1_000,
            dequeue_perf_ns=3_000,
        ),
        exec_start_ns=5_000,
        exec_end_ns=9_000,
    )
    assert latency is not None
    counts: dict[GpuRequestType, int] = {}
    total: dict[GpuRequestType, float] = {}
    max_total: dict[GpuRequestType, float] = {}
    samples: dict[GpuRequestType, list[float]] = {}
    queue_total: dict[GpuRequestType, float] = {}
    queue_max: dict[GpuRequestType, float] = {}
    queue_samples: dict[GpuRequestType, list[float]] = {}
    in_exec_total: dict[GpuRequestType, float] = {}
    in_exec_max: dict[GpuRequestType, float] = {}
    in_exec_samples: dict[GpuRequestType, list[float]] = {}

    from collections import defaultdict

    counts = defaultdict(int, counts)
    total = defaultdict(float, total)
    max_total = defaultdict(float, max_total)
    samples = defaultdict(list, samples)
    queue_total = defaultdict(float, queue_total)
    queue_max = defaultdict(float, queue_max)
    queue_samples = defaultdict(list, queue_samples)
    in_exec_total = defaultdict(float, in_exec_total)
    in_exec_max = defaultdict(float, in_exec_max)
    in_exec_samples = defaultdict(list, in_exec_samples)

    assert record_request_latency_stats(
        latency,
        lat_counts=counts,
        lat_total_sec=total,
        lat_max_sec=max_total,
        lat_samples=samples,
        lat_queue_total_sec=queue_total,
        lat_queue_max_sec=queue_max,
        lat_queue_samples=queue_samples,
        lat_in_exec_total_sec=in_exec_total,
        lat_in_exec_max_sec=in_exec_max,
        lat_in_exec_samples=in_exec_samples,
        sample_cap=4,
    )

    req_type = GpuRequestType.GPU_NATIVE_GA_RUN
    assert counts[req_type] == 1
    assert total[req_type] == latency.total_sec
    assert max_total[req_type] == latency.total_sec
    assert queue_total[req_type] == latency.queue_sec
    assert queue_max[req_type] == latency.queue_sec
    assert in_exec_total[req_type] == latency.in_exec_sec
    assert in_exec_max[req_type] == latency.in_exec_sec
    assert samples[req_type] == [latency.total_sec]
    assert queue_samples[req_type] == [latency.queue_sec]
    assert in_exec_samples[req_type] == [latency.in_exec_sec]


def test_record_request_latency_stats_uses_reservoir_replacement():
    from collections import defaultdict

    req_type = GpuRequestType.LOAD_REF_ARRAYS
    latency = compute_request_latency_window(
        GpuRequest(
            request_type=req_type,
            request_id=4,
            worker_id=0,
            payload={},
            submit_perf_ns=1_000,
            dequeue_perf_ns=2_000,
        ),
        exec_start_ns=2_000,
        exec_end_ns=6_000,
    )
    assert latency is not None
    counts = defaultdict(int, {req_type: 4})
    total = defaultdict(float)
    max_total = defaultdict(float)
    samples = defaultdict(list, {req_type: [0.1, 0.2]})
    queue_total = defaultdict(float)
    queue_max = defaultdict(float)
    queue_samples = defaultdict(list, {req_type: [0.01, 0.02]})
    in_exec_total = defaultdict(float)
    in_exec_max = defaultdict(float)
    in_exec_samples = defaultdict(list, {req_type: [0.03, 0.04]})

    assert record_request_latency_stats(
        latency,
        lat_counts=counts,
        lat_total_sec=total,
        lat_max_sec=max_total,
        lat_samples=samples,
        lat_queue_total_sec=queue_total,
        lat_queue_max_sec=queue_max,
        lat_queue_samples=queue_samples,
        lat_in_exec_total_sec=in_exec_total,
        lat_in_exec_max_sec=in_exec_max,
        lat_in_exec_samples=in_exec_samples,
        sample_cap=2,
        randint_fn=lambda _low, _high: 1,
    )

    assert counts[req_type] == 5
    assert samples[req_type] == [0.1, latency.total_sec]
    assert queue_samples[req_type] == [0.01, latency.queue_sec]
    assert in_exec_samples[req_type] == [0.03, latency.in_exec_sec]


def test_build_executor_idle_summary_reports_idle_windows():
    summary = build_executor_idle_summary(
        idle_gaps=[0.01, 0.02, 0.03],
        loop_start_ts=10.0,
        first_work_ts=10.25,
        shutdown_ts=20.0,
        last_work_end_ts=19.5,
    )

    assert summary.total_sec == 0.06
    assert summary.max_sec == 0.03
    assert summary.p95_sec == 0.03
    assert summary.initial_sec == 0.25
    assert summary.tail_sec == 0.5


def test_build_executor_idle_summary_clamps_missing_and_reversed_windows():
    summary = build_executor_idle_summary(
        idle_gaps=None,
        loop_start_ts=10.0,
        first_work_ts=9.0,
        shutdown_ts=19.0,
        last_work_end_ts=20.0,
    )

    assert summary.total_sec == 0.0
    assert summary.max_sec == 0.0
    assert summary.p95_sec == 0.0
    assert summary.initial_sec == 0.0
    assert summary.tail_sec == 0.0


def test_build_request_latency_summary_sorts_rows_and_formats_log_parts():
    rows = build_request_latency_summary(
        lat_counts={
            GpuRequestType.LOAD_REF_ARRAYS: 2,
            GpuRequestType.GPU_NATIVE_GA_RUN: 1,
        },
        lat_total_sec={
            GpuRequestType.LOAD_REF_ARRAYS: 0.020,
            GpuRequestType.GPU_NATIVE_GA_RUN: 0.050,
        },
        lat_samples={
            GpuRequestType.LOAD_REF_ARRAYS: [0.008, 0.012],
            GpuRequestType.GPU_NATIVE_GA_RUN: [0.050],
        },
        lat_queue_total_sec={
            GpuRequestType.LOAD_REF_ARRAYS: 0.004,
            GpuRequestType.GPU_NATIVE_GA_RUN: 0.010,
        },
        lat_queue_samples={
            GpuRequestType.LOAD_REF_ARRAYS: [0.001, 0.003],
            GpuRequestType.GPU_NATIVE_GA_RUN: [0.010],
        },
        lat_in_exec_total_sec={
            GpuRequestType.LOAD_REF_ARRAYS: 0.006,
            GpuRequestType.GPU_NATIVE_GA_RUN: 0.020,
        },
        lat_in_exec_samples={
            GpuRequestType.LOAD_REF_ARRAYS: [0.002, 0.004],
            GpuRequestType.GPU_NATIVE_GA_RUN: [0.020],
        },
    )

    assert [row.request_type for row in rows] == [
        GpuRequestType.GPU_NATIVE_GA_RUN,
        GpuRequestType.LOAD_REF_ARRAYS,
    ]
    assert rows[0].count == 1
    assert rows[0].total_avg_sec == 0.050
    assert rows[0].format_log_part() == (
        "gpu_native_ga_run:n=1 total_avg=50.0ms p95=50.0ms "
        "queue_avg=10.0ms p95=10.0ms in_exec_avg=20.0ms p95=20.0ms"
    )
    assert request_latency_summary_log_message(rows[:1]) == (
        "[GpuExecutor][LATENCY] gpu_native_ga_run:n=1 total_avg=50.0ms p95=50.0ms "
        "queue_avg=10.0ms p95=10.0ms in_exec_avg=20.0ms p95=20.0ms"
    )


def test_build_request_latency_summary_skips_empty_counts_and_honors_limit():
    rows = build_request_latency_summary(
        lat_counts={
            GpuRequestType.LOAD_REF_ARRAYS: 0,
            GpuRequestType.GPU_NATIVE_GA_RUN: 2,
        },
        lat_total_sec={GpuRequestType.GPU_NATIVE_GA_RUN: 0.020},
        lat_samples={},
        lat_queue_total_sec={GpuRequestType.GPU_NATIVE_GA_RUN: 0.004},
        lat_queue_samples={},
        lat_in_exec_total_sec={GpuRequestType.GPU_NATIVE_GA_RUN: 0.006},
        lat_in_exec_samples={},
        limit=1,
    )

    assert len(rows) == 1
    assert rows[0].request_type == GpuRequestType.GPU_NATIVE_GA_RUN
    assert rows[0].total_p95_sec == 0.0
    assert rows[0].queue_p95_sec == 0.0
    assert rows[0].in_exec_p95_sec == 0.0
    assert request_latency_summary_log_message([]) is None


def test_build_exec_breakdown_summary_sorts_and_formats_rows():
    rows = build_exec_breakdown_summary(
        req_type_exec_sec={
            GpuRequestType.LOAD_REF_ARRAYS: 0.5,
            GpuRequestType.GPU_NATIVE_GA_RUN: 2.0,
        },
        req_type_host_sec={GpuRequestType.GPU_NATIVE_GA_RUN: 0.75},
        req_type_gpu_kernel_sec={GpuRequestType.GPU_NATIVE_GA_RUN: 1.0},
        req_type_gpu_upload_sec={GpuRequestType.GPU_NATIVE_GA_RUN: 0.10},
        req_type_gpu_download_sec={GpuRequestType.GPU_NATIVE_GA_RUN: 0.15},
    )

    assert [row.request_type for row in rows] == [
        GpuRequestType.GPU_NATIVE_GA_RUN,
        GpuRequestType.LOAD_REF_ARRAYS,
    ]
    assert rows[0].format_log_part() == (
        "gpu_native_ga_run:exec=2.00s host~=0.75s gpu_kernel~=1.00s up~=0.10s down~=0.15s"
    )
    assert exec_breakdown_summary_log_message(rows[:1]) == (
        "[GpuExecutor][BREAKDOWN] "
        "gpu_native_ga_run:exec=2.00s host~=0.75s gpu_kernel~=1.00s up~=0.10s down~=0.15s"
    )
    assert rows[1].host_sec == 0.0
    assert rows[1].gpu_kernel_sec == 0.0
    assert rows[1].gpu_upload_sec == 0.0
    assert rows[1].gpu_download_sec == 0.0


def test_build_exec_breakdown_summary_skips_invalid_exec_and_honors_limit():
    rows = build_exec_breakdown_summary(
        req_type_exec_sec={
            GpuRequestType.LOAD_REF_ARRAYS: "bad",
            GpuRequestType.GPU_NATIVE_GA_RUN: 2.0,
        },
        req_type_host_sec={},
        req_type_gpu_kernel_sec={},
        req_type_gpu_upload_sec={},
        req_type_gpu_download_sec={},
        limit=1,
    )

    assert len(rows) == 1
    assert rows[0].request_type == GpuRequestType.GPU_NATIVE_GA_RUN
    assert exec_breakdown_summary_log_message([]) is None


def test_build_idle_transition_summary_sorts_and_formats_rows():
    rows = build_idle_transition_summary(
        idle_transitions_sec={
            (None, GpuRequestType.GPU_NATIVE_GA_RUN): 1.25,
            (GpuRequestType.GPU_NATIVE_GA_RUN, None): 2.5,
        },
        idle_transitions_count={
            (None, GpuRequestType.GPU_NATIVE_GA_RUN): 3,
            (GpuRequestType.GPU_NATIVE_GA_RUN, None): 1,
        },
    )

    assert [row.previous_type for row in rows] == [GpuRequestType.GPU_NATIVE_GA_RUN, None]
    assert rows[0].next_type is None
    assert rows[0].format_log_part() == "gpu_native_ga_run-><none>:2.50s(1)"
    assert rows[1].format_log_part() == "<start>->gpu_native_ga_run:1.25s(3)"
    assert idle_transition_summary_log_message(rows) == (
        "[GpuExecutor][IDLE] transitions=[gpu_native_ga_run-><none>:2.50s(1), "
        "<start>->gpu_native_ga_run:1.25s(3)]"
    )


def test_build_idle_transition_summary_skips_invalid_keys_and_honors_limit():
    rows = build_idle_transition_summary(
        idle_transitions_sec={
            "bad": 9.0,
            (GpuRequestType.LOAD_REF_ARRAYS, GpuRequestType.GPU_NATIVE_GA_RUN): 1.0,
            (GpuRequestType.GPU_NATIVE_GA_RUN, None): 2.0,
        },
        idle_transitions_count={
            (GpuRequestType.LOAD_REF_ARRAYS, GpuRequestType.GPU_NATIVE_GA_RUN): 2,
            (GpuRequestType.GPU_NATIVE_GA_RUN, None): 4,
        },
        limit=1,
    )

    assert len(rows) == 1
    assert rows[0].previous_type == GpuRequestType.GPU_NATIVE_GA_RUN
    assert rows[0].count == 4
    assert idle_transition_summary_log_message([]) is None


def test_executor_profile_log_message_preserves_profile_format():
    idle_summary = build_executor_idle_summary(
        idle_gaps=[0.01, 0.03],
        loop_start_ts=10.0,
        first_work_ts=10.1,
        shutdown_ts=20.0,
        last_work_end_ts=19.75,
    )

    message = executor_profile_log_message(
        wait_sec=1.0,
        exec_sec=3.0,
        requests_processed=6,
        batch_size_sum=10,
        batches_observed=2,
        pack_sec=0.25,
        req_type_exec_sec={
            GpuRequestType.LOAD_REF_ARRAYS: 0.5,
            GpuRequestType.GPU_NATIVE_GA_RUN: 2.0,
        },
        req_type_counts={
            GpuRequestType.LOAD_REF_ARRAYS: 1,
            GpuRequestType.GPU_NATIVE_GA_RUN: 3,
        },
        req_type_pack_sec={
            GpuRequestType.GPU_NATIVE_GA_RUN: 0.20,
            GpuRequestType.LOAD_REF_ARRAYS: 0.0,
        },
        batch_size_counts={1: 2, 4: 3},
        fg_tasks_batches=2,
        fg_tasks_total=12,
        fg_tasks_max=8,
        fg_tasks_batch_hist={4: 1, 8: 1},
        idle_gaps_count=2,
        idle_summary=idle_summary,
    )

    assert message == (
        "[GpuExecutor][PROFILE] wait=1.00s exec=3.00s busy=75.0% (executor) "
        "avg_exec_per_req=0.500s avg_batch=5.00 pack=0.25s "
        "pack_types=[gpu_native_ga_run:0.20s] idle_gaps=2 idle_sum=0.04s "
        "idle_max=0.030s idle_p95=0.030s idle_initial=0.100s idle_tail=0.250s "
        "types=[gpu_native_ga_run:3 (2.00s), load_ref_arrays:1 (0.50s)] "
        "batch_sizes=[1:2, 4:3] fg_task_batches=2 fg_tasks_total=12 "
        "fg_tasks_avg=6.0 fg_tasks_max=8 fg_tasks_hist=[4:1, 8:1]"
    )


def test_executor_profile_log_message_handles_empty_counts():
    idle_summary = build_executor_idle_summary(
        idle_gaps=[],
        loop_start_ts=None,
        first_work_ts=None,
        shutdown_ts=None,
        last_work_end_ts=None,
    )

    message = executor_profile_log_message(
        wait_sec=0.0,
        exec_sec=0.0,
        requests_processed=0,
        batch_size_sum=0,
        batches_observed=0,
        pack_sec=0.0,
        req_type_exec_sec={},
        req_type_counts={},
        req_type_pack_sec={},
        batch_size_counts={},
        fg_tasks_batches=0,
        fg_tasks_total=0,
        fg_tasks_max=0,
        fg_tasks_batch_hist={},
        idle_gaps_count=0,
        idle_summary=idle_summary,
    )

    assert "busy=0.0%" in message
    assert "avg_exec_per_req=0.000s" in message
    assert "avg_batch=0.00" in message
    assert "fg_tasks_avg=0.0" in message


def test_fg_tasks_per_sec_log_message_formats_when_fg_work_exists():
    message = fg_tasks_per_sec_log_message(
        req_type_exec_sec={GpuRequestType.SOLVE_FORCE_GREATS_FINDER: 2.0},
        fg_tasks_total=10,
    )

    assert message == "[GpuExecutor][FG] tasks_per_sec~=5.0 (executor-wall) fg_exec=2.00s"


def test_fg_tasks_per_sec_log_message_skips_missing_or_empty_fg_work():
    assert fg_tasks_per_sec_log_message(req_type_exec_sec={}, fg_tasks_total=10) is None
    assert (
        fg_tasks_per_sec_log_message(
            req_type_exec_sec={GpuRequestType.SOLVE_FORCE_GREATS_FINDER: 2.0},
            fg_tasks_total=0,
        )
        is None
    )


def test_build_executor_profile_stats_shapes_profile_payload():
    stats = build_executor_profile_stats(
        wait_sec=1.0,
        exec_sec=3.0,
        batches_observed=2,
        batch_size_sum=10,
        workload_events_emitted=4,
        last_batch_plan_mode="throughput",
        workload_units_samples=[10.0, 30.0],
        workload_age_ms_samples=[2.0, 6.0],
        req_type_counts={GpuRequestType.GPU_NATIVE_GA_RUN: 3},
        req_type_host_sec={GpuRequestType.GPU_NATIVE_GA_RUN: 1.5},
        req_type_gpu_kernel_sec={GpuRequestType.GPU_NATIVE_GA_RUN: 0.75},
        req_type_gpu_upload_sec={GpuRequestType.GPU_NATIVE_GA_RUN: 0.25},
        req_type_gpu_download_sec={GpuRequestType.GPU_NATIVE_GA_RUN: 0.5},
    )

    assert stats == {
        "wait_sec": 1.0,
        "exec_sec": 3.0,
        "utilization_pct": 75.0,
        "batches_observed": 2,
        "avg_batch_size": 5.0,
        "workload_events_emitted": 4,
        "last_batch_mode": "throughput",
        "avg_work_units": 20.0,
        "avg_submit_age_ms": 4.0,
        "exec_breakdown_sec_by_type": {
            "gpu_native_ga_run": {
                "host_sec": 1.5,
                "gpu_kernel_sec": 0.75,
                "gpu_upload_sec": 0.25,
                "gpu_download_sec": 0.5,
            }
        },
    }


def test_build_executor_profile_stats_handles_empty_samples_and_zero_total():
    stats = build_executor_profile_stats(
        wait_sec=0.0,
        exec_sec=0.0,
        batches_observed=0,
        batch_size_sum=0,
        workload_events_emitted=0,
        last_batch_plan_mode="",
        workload_units_samples=[],
        workload_age_ms_samples=[],
        req_type_counts={},
        req_type_host_sec={},
        req_type_gpu_kernel_sec={},
        req_type_gpu_upload_sec={},
        req_type_gpu_download_sec={},
    )

    assert stats["utilization_pct"] == 0.0
    assert stats["avg_batch_size"] == 0.0
    assert stats["avg_work_units"] == 0.0
    assert stats["avg_submit_age_ms"] == 0.0
    assert stats["exec_breakdown_sec_by_type"] == {}


def test_build_executor_stats_includes_profile_only_when_present():
    assert build_executor_stats(requests_processed=7, registered_workers=2) == {
        "requests_processed": 7,
        "registered_workers": 2,
    }

    assert build_executor_stats(
        requests_processed=7,
        registered_workers=2,
        profile={"wait_sec": 1.5},
    ) == {
        "requests_processed": 7,
        "registered_workers": 2,
        "profile": {"wait_sec": 1.5},
    }
