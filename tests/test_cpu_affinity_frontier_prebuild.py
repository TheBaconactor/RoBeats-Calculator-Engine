from __future__ import annotations


def test_cpu_affinity_sizes_frontier_prebuild_workers_and_threads(monkeypatch) -> None:
    from gear_optimizer.core import cpu_affinity

    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 32)
    monkeypatch.setattr(
        cpu_affinity,
        "timeline_prebuild_worker_count",
        lambda: cpu_affinity.frontier_prebuild_worker_count(),
    )

    assert cpu_affinity.frontier_prebuild_worker_count() == 8
    assert cpu_affinity.timeline_prebuild_worker_count() == 8
    assert cpu_affinity.frontier_prebuild_intra_worker_threads(8) == 4
