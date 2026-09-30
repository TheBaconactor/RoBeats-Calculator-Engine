"""Timing mode is an explicit semantic input, never a deployment-wide coercion."""

from __future__ import annotations

import io

import pytest


def test_service_request_gate_preserves_each_supported_mode():
    from gear_optimizer import robeatsmeta_service

    assert robeatsmeta_service._normalize_timing_mode("perfect_window") == "perfect_window"
    assert robeatsmeta_service._normalize_timing_mode("zero_ms") == "zero_ms"
    with pytest.raises(robeatsmeta_service.RequestError):
        robeatsmeta_service._normalize_timing_mode("bogus")


def test_song_preparation_uses_chart_timing_metadata(tmp_path):
    from gear_optimizer.solver.song_preparation import prepare_song

    chart = tmp_path / "zero_ms_chart.txt"
    chart.write_text(
        "Song Name\tZero Chart\nDifficulty\tHard\nPrimary Color\tRush\nSecondary Color\tFlow\n"
        "Last Note Time\t0.4\nLong Notes\t0\nTiming Mode\tzero_ms\nSong Data\n0.0 1 0 1\n0.4 2 1 1\n",
        encoding="utf-8",
    )
    assert prepare_song(str(chart)).mode == "zero_ms"


def test_startup_prepares_both_frontier_cache_families(monkeypatch):
    from gear_optimizer.solver import cpu_work_manager

    calls: dict[str, list[tuple[str, ...]]] = {"timeline": [], "fg": []}

    class Summary:
        total = completed = failures = built = disk = memory = 0

    def fake_timeline(**kwargs):
        calls["timeline"].append(tuple(kwargs["timing_modes"]))
        return Summary()

    def fake_fg(**kwargs):
        calls["fg"].append(tuple(kwargs["timing_modes"]))
        return Summary()

    monkeypatch.setattr(cpu_work_manager, "run_timeline_frontier_cache_prebuild", fake_timeline)
    monkeypatch.setattr(cpu_work_manager, "run_fg_response_frontier_cache_prebuild", fake_fg)
    cpu_work_manager.run_startup_cpu_work(
        song_queue=["chart.txt"],
        curves={},
        data_root=".",
        announce_stream=io.StringIO(),
    )
    assert calls == {
        "timeline": [("perfect_window", "zero_ms")],
        "fg": [("perfect_window", "zero_ms")],
    }


def test_gpu_warmup_songs_do_not_select_a_request_mode():
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    assert "Timing Mode" not in ga_operations._warmup_song().chart.header
