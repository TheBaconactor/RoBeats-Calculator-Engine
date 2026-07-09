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


def test_timeline_prebuild_worker_count_caps_by_available_ram(monkeypatch) -> None:
    """Timeline builds peak modestly and uniformly, so a flat per-worker RAM cap is its honest
    model. (FG has no flat cap: its per-song peak spans ~4x, so its concurrency is owned by the
    memory-weighted admission scheduler in fg_response_frontier_cache_prebuild.)"""
    from gear_optimizer.core import cpu_affinity

    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 32)  # 31 CPU-budget workers

    import psutil

    class _FakeVM:
        available = int(10 * 1e9)  # 10 GB available

    monkeypatch.setattr(psutil, "virtual_memory", lambda: _FakeVM())

    # 10 GB / 1.5 GB-per-worker -> 6 workers, below the 31-worker CPU budget.
    assert cpu_affinity.timeline_prebuild_worker_count() == 6


def test_timeline_prebuild_worker_count_floor_is_one(monkeypatch) -> None:
    """Even under severe memory pressure at least one worker is scheduled (the guard is a cap, and
    the build must still make progress)."""
    from gear_optimizer.core import cpu_affinity

    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 32)

    import psutil

    class _FakeVM:
        available = int(0.5 * 1e9)  # 0.5 GB available

    monkeypatch.setattr(psutil, "virtual_memory", lambda: _FakeVM())

    assert cpu_affinity.timeline_prebuild_worker_count() == 1


def test_fg_response_flat_worker_ram_cap_is_deleted() -> None:
    """The flat FG GB-per-worker cap admitted 12 workers x ~7 GB measured giant commit and crashed
    the machine (2026-07-09). Its one canonical replacement is the weighted admission scheduler;
    the superseded route must not resurface."""
    from gear_optimizer.core import cpu_affinity

    assert not hasattr(cpu_affinity, "fg_response_prebuild_worker_count")
    assert not hasattr(cpu_affinity, "FG_RESPONSE_PREBUILD_GB_PER_WORKER")


def test_windows_band_pinning_uses_full_frontier_set_on_uniform_cores(monkeypatch) -> None:
    """On uniform silicon (no E-cores) every worker gets the full frontier CPU set: weighted
    admission varies live concurrency with per-song memory weight, so fixed per-worker bands would
    strand a giant's reducer threads on a 1-CPU band while sibling bands idle."""
    from gear_optimizer.core import cpu_affinity

    masks: list[int] = []
    monkeypatch.setattr(cpu_affinity.sys, "platform", "win32")
    monkeypatch.setattr(cpu_affinity, "logical_core_count", lambda: 4)
    monkeypatch.setattr(
        cpu_affinity,
        "_windows_logical_cpu_efficiency_classes",
        lambda: [(0, 0), (1, 0), (2, 0), (3, 0)],
    )
    monkeypatch.setattr(cpu_affinity, "_apply_affinity_mask", lambda mask: masks.append(int(mask)))

    for index in range(3):
        cpu_affinity.pin_current_process_to_core_band(index, 3)

    # Reserved weakest CPU (index 3) stays excluded; every worker spans the whole frontier set.
    assert masks == [0b0111, 0b0111, 0b0111]
