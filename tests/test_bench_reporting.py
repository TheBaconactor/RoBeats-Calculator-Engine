import tools.bench._bench_reporting as bench_reporting


def test_normalize_kernel_names_dedupes_and_strips():
    assert bench_reporting.normalize_kernel_names(
        [" base_stage ", "", "base_stage", "fg_stage", "  fg_stage  ", None]
    ) == ["base_stage", "fg_stage"]


def test_add_kernel_profiler_kernel_entries_computes_accounting(monkeypatch):
    monkeypatch.setattr(
        bench_reporting,
        "get_taichi_kernel_profiler_kernel_entries",
        lambda kernel_names, enabled: [
            {"name": "k1", "counter": 2, "avg_ms": 1.0, "min_ms": 0.9, "max_ms": 1.1, "total_sec": 0.002},
            {"name": "k2", "counter": 1, "avg_ms": 3.0, "min_ms": 3.0, "max_ms": 3.0, "total_sec": 0.003},
        ],
    )
    result = {"kernel_profiler_total_sec": 0.010}

    bench_reporting.add_kernel_profiler_kernel_entries(
        result,
        enabled=True,
        kernel_names=["k1", "k2"],
    )

    assert [entry["name"] for entry in result["kernel_profiler_kernels"]] == ["k1", "k2"]
    assert result["kernel_profiler_accounted_total_sec"] == 0.005
    assert result["kernel_profiler_unaccounted_total_sec"] == 0.005
    assert result["kernel_profiler_accounted_pct"] == 50.0


def test_add_kernel_profiler_kernel_entries_handles_missing_total(monkeypatch):
    monkeypatch.setattr(
        bench_reporting,
        "get_taichi_kernel_profiler_kernel_entries",
        lambda kernel_names, enabled: [{"name": "k1", "counter": 1, "avg_ms": 1.0, "min_ms": 1.0, "max_ms": 1.0, "total_sec": 0.001}],
    )
    result = {"kernel_profiler_total_sec": None}

    bench_reporting.add_kernel_profiler_kernel_entries(
        result,
        enabled=True,
        kernel_names=["k1"],
    )

    assert result["kernel_profiler_accounted_total_sec"] == 0.001
    assert result["kernel_profiler_unaccounted_total_sec"] is None
    assert result["kernel_profiler_accounted_pct"] is None
