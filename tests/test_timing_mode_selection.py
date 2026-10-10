"""Timing mode is an explicit semantic input, never a deployment-wide coercion."""

from __future__ import annotations

import io

import pytest


def test_service_request_gate_preserves_each_supported_mode():
    from gear_optimizer import robeatsmeta_service

    assert robeatsmeta_service._normalize_timing_mode(None) == "non-precise"
    assert robeatsmeta_service._normalize_timing_mode("precise") == "precise"
    assert robeatsmeta_service._normalize_timing_mode("non-precise") == "non-precise"
    for mode in ("bogus", "perfect_window", "zero_ms", "frame_robust"):
        with pytest.raises(robeatsmeta_service.RequestError):
            robeatsmeta_service._normalize_timing_mode(mode)


def test_startup_prepares_both_frontier_cache_families_per_mode(monkeypatch):
    from gear_optimizer.solver import cpu_work_manager

    calls: dict[str, list[dict]] = {"timeline": [], "fg": []}

    class Summary:
        total = completed = failures = built = disk = memory = 0
        elapsed_ms = 0.0

    def fake_prebuild(prebuild, **kwargs):
        calls[{"timeline": "timeline", "fg_response": "fg"}[prebuild.cache.name]].append(kwargs["charts_by_mode"])
        return Summary()

    monkeypatch.setattr(cpu_work_manager, "prebuild_frontier_cache", fake_prebuild)
    charts_by_mode = {"precise": ["chart.txt"], "non-precise": ["chart.txt", "pinned.txt"]}
    cpu_work_manager.run_startup_cpu_work(charts_by_mode=charts_by_mode, curves={}, announce_stream=io.StringIO())
    assert calls == {"timeline": [charts_by_mode], "fg": [charts_by_mode]}


def test_gpu_warmup_songs_do_not_select_a_request_mode():
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    assert "Timing Mode" not in ga_operations._warmup_song().chart.header
