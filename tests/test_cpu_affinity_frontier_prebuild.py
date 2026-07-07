from __future__ import annotations


def test_cpu_affinity_sizes_frontier_prebuild_to_all_but_one_cpu(monkeypatch) -> None:
    from gear_optimizer.core import cpu_affinity

    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 10)
    monkeypatch.setattr(
        cpu_affinity,
        "timeline_prebuild_worker_count",
        lambda: cpu_affinity.frontier_prebuild_worker_count(),
    )

    assert cpu_affinity.frontier_prebuild_cpu_count() == 9
    assert cpu_affinity.frontier_prebuild_worker_count() == 9
    assert cpu_affinity.timeline_prebuild_worker_count() == 9
    assert cpu_affinity.frontier_prebuild_intra_worker_threads(9) == 1
    assert cpu_affinity.frontier_prebuild_intra_worker_threads(3) == 3


def test_frontier_prebuild_reserves_one_weakest_efficiency_cpu() -> None:
    from gear_optimizer.core import cpu_affinity

    assert cpu_affinity._frontier_prebuild_cpu_indices_from_efficiency(
        [(0, 1), (1, 1), (2, 0), (3, 0)],
        4,
    ) == [0, 1, 2]
    assert cpu_affinity._frontier_prebuild_cpu_indices_from_efficiency(
        [(0, 0), (1, 0), (2, 0), (3, 0)],
        4,
    ) == [0, 1, 2]
    assert cpu_affinity._frontier_prebuild_cpu_indices_from_efficiency(None, 1) == [0]


def test_windows_frontier_band_pinning_excludes_reserved_e_core(monkeypatch) -> None:
    from gear_optimizer.core import cpu_affinity

    masks: list[int] = []
    monkeypatch.setattr(cpu_affinity.sys, "platform", "win32")
    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 4)
    monkeypatch.setattr(
        cpu_affinity,
        "_windows_logical_cpu_efficiency_classes",
        lambda: [(0, 1), (1, 1), (2, 0), (3, 0)],
    )
    monkeypatch.setattr(cpu_affinity, "_apply_affinity_mask", lambda mask: masks.append(int(mask)))

    for index in range(3):
        cpu_affinity.pin_current_process_to_core_band(index, 3)

    assert masks == [0b001, 0b010, 0b100]
    assert (masks[0] | masks[1] | masks[2]) == 0b0111


def test_fg_response_prebuild_worker_count_caps_by_available_ram(monkeypatch) -> None:
    """The FG cold build is the multi-GB one and runs heaviest-first, so its worker count must be
    capped by available RAM at the FG per-worker budget -- not left at the raw core-derived count."""
    from gear_optimizer.core import cpu_affinity

    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 32)  # 31 CPU-budget workers

    import psutil

    class _FakeVM:
        available = int(10 * 1e9)  # 10 GB available

    monkeypatch.setattr(psutil, "virtual_memory", lambda: _FakeVM())

    # 10 GB / 4 GB-per-worker -> 2 workers, below the 31-worker CPU budget.
    assert cpu_affinity.FG_RESPONSE_PREBUILD_GB_PER_WORKER == 4.0
    assert cpu_affinity.fg_response_prebuild_worker_count() == 2
    # Timeline's lighter 1.5 GB budget allows more workers from the same RAM.
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
