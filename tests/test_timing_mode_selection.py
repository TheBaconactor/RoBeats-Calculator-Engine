"""Timing mode is an explicit semantic input, never a deployment-wide coercion."""

from __future__ import annotations

import io

import pytest


def test_a_service_request_keeps_each_supported_mode():
    from gear_optimizer import robeatsmeta_service

    def mode_of(value):
        return robeatsmeta_service.parse_request({"chartText": "Song Data\n", "timingMode": value}).timing_mode

    assert mode_of(None) == "non-precise"
    assert mode_of("precise") == "precise"
    assert mode_of("non-precise") == "non-precise"
    for mode in ("bogus", "perfect_window", "zero_ms", "frame_robust"):
        with pytest.raises(robeatsmeta_service.RequestError):
            mode_of(mode)


def test_startup_prepares_both_frontier_cache_families_per_mode(monkeypatch):
    from gear_optimizer.frontier import startup_prebuild

    calls: dict[str, list[dict]] = {"timeline": [], "fg": []}

    class Summary:
        total = completed = failures = built = disk = memory = 0
        elapsed_ms = 0.0

    def fake_prebuild(prebuild, **kwargs):
        calls[{"timeline": "timeline", "fg_response": "fg"}[prebuild.cache.name]].append(kwargs["charts_by_mode"])
        return Summary()

    monkeypatch.setattr(startup_prebuild, "prebuild_frontier_cache", fake_prebuild)
    charts_by_mode = {"precise": ["chart.txt"], "non-precise": ["chart.txt", "pinned.txt"]}
    startup_prebuild.run_startup_cpu_work(charts_by_mode=charts_by_mode, curves={}, announce_stream=io.StringIO())
    assert calls == {"timeline": [charts_by_mode], "fg": [charts_by_mode]}


def test_gpu_warmup_songs_do_not_select_a_request_mode():
    from gear_optimizer.gpu import ga

    assert "Timing Mode" not in ga._warmup_song().chart.header
