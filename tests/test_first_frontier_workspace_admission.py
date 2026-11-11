from __future__ import annotations

from types import SimpleNamespace

import pytest

from gear_optimizer.frontier import producer_reducer as reducer


def test_workspace_plan_reports_exact_numpy_allocation_bytes() -> None:
    plan = reducer.WorkspacePlan(n=100, pair_mod_bound=25)
    expected = 4 * (
        3 * ((100 + 1) * 25)
        + 2 * (100 + 2)
        + 4 * (100 + 1)
    )
    assert plan.bytes_per_thread == expected


def _available(monkeypatch, available: int) -> None:
    monkeypatch.setattr(reducer.psutil, "virtual_memory", lambda: SimpleNamespace(available=available))


def test_workspace_admission_fails_before_impossible_allocation(monkeypatch) -> None:
    plan = reducer.WorkspacePlan(n=20_000, pair_mod_bound=20_001)
    required = plan.bytes_per_thread * 4
    _available(monkeypatch, required)

    with pytest.raises(MemoryError, match=r"rejected before allocation.*4 worker"):
        reducer.admit_workspaces(plan, 4)


def test_workspace_admission_accepts_exact_plan_with_system_headroom(monkeypatch) -> None:
    plan = reducer.WorkspacePlan(n=100, pair_mod_bound=25)
    required = plan.bytes_per_thread * 2
    _available(monkeypatch, required * 2)

    reducer.admit_workspaces(plan, 2)
    # A quarter of the available memory stays reserved: 4/3 of one byte less than the need is rejected.
    _available(monkeypatch, 4 * (required - 1) // 3)
    with pytest.raises(MemoryError, match=r"rejected before allocation.*2 worker"):
        reducer.admit_workspaces(plan, 2)
