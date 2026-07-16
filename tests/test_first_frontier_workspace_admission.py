from __future__ import annotations

import pytest

from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_reducer as reducer


def test_workspace_plan_reports_exact_numpy_allocation_bytes() -> None:
    plan = reducer._FirstFrontierWorkspacePlan(n=100, pair_mod_bound=25)
    expected = 4 * (
        3 * ((100 + 1) * 25)
        + 2 * (25 + 1)
        + 2 * ((25 + 1) * (100 + 2))
        + 4 * (100 + 1)
    )
    assert plan.bytes_per_thread == expected


def test_workspace_admission_fails_before_impossible_allocation(monkeypatch) -> None:
    plan = reducer._FirstFrontierWorkspacePlan(n=20_000, pair_mod_bound=20_001)
    required = plan.bytes_per_thread * 4
    monkeypatch.setattr(reducer, "_first_frontier_available_memory_bytes", lambda: required)

    with pytest.raises(MemoryError, match=r"rejected before allocation.*4 worker"):
        reducer._admit_first_frontier_workspace(plan, worker_count=4)
    assert plan.allocations == 0
    assert plan.allocated_bytes == 0


def test_workspace_admission_accepts_exact_plan_with_system_headroom(monkeypatch) -> None:
    plan = reducer._FirstFrontierWorkspacePlan(n=100, pair_mod_bound=25)
    required = plan.bytes_per_thread * 2
    monkeypatch.setattr(reducer, "_first_frontier_available_memory_bytes", lambda: required * 2)

    assert reducer._admit_first_frontier_workspace(plan, worker_count=2) == required
    assert plan.allocations == 0
