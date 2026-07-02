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


def test_fg_response_prebuild_worker_count_caps_by_available_ram(monkeypatch) -> None:
    """The FG cold build is the multi-GB one and runs heaviest-first, so its worker count must be
    capped by available RAM at the FG per-worker budget -- not left at the raw core-derived count."""
    from gear_optimizer.core import cpu_affinity

    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 32)  # 8 core-derived workers

    import psutil

    class _FakeVM:
        available = int(10 * 1e9)  # 10 GB available

    monkeypatch.setattr(psutil, "virtual_memory", lambda: _FakeVM())

    # 10 GB / 4 GB-per-worker -> 2 workers, below the 8-worker core budget.
    assert cpu_affinity.FG_RESPONSE_PREBUILD_GB_PER_WORKER == 4.0
    assert cpu_affinity.fg_response_prebuild_worker_count() == 2
    # Timeline's lighter 1.5 GB budget allows more workers from the same RAM (capped at 8 cores).
    assert cpu_affinity.timeline_prebuild_worker_count() == 6


def test_fg_response_prebuild_worker_count_floor_is_one(monkeypatch) -> None:
    """Even under severe memory pressure at least one worker is scheduled (the guard is a cap, and
    the build must still make progress)."""
    from gear_optimizer.core import cpu_affinity

    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 32)

    import psutil

    class _FakeVM:
        available = int(0.5 * 1e9)  # 0.5 GB available

    monkeypatch.setattr(psutil, "virtual_memory", lambda: _FakeVM())

    assert cpu_affinity.fg_response_prebuild_worker_count() == 1
