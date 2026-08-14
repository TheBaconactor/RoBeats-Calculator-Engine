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


def test_song_preparation_uses_chart_timing_metadata(monkeypatch):
    captured: dict = {}

    def fake_envelope(calc_song, *, mode=None, **_kwargs):
        captured["mode"] = mode
        return calc_song

    monkeypatch.setattr("gear_optimizer.solver.timing_envelope.apply_timing_envelope", fake_envelope)
    from gear_optimizer.solver import song_preparation

    song_preparation._apply_timing_envelope(
        {"song_data": {}, "metadata": {"Timing Mode": "zero_ms"}}
    )
    assert captured["mode"] is None


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
        cfg=None,
        song_queue=["chart.txt"],
        ref_arrays={},
        data_root=".",
        announce_stream=io.StringIO(),
    )
    assert calls == {
        "timeline": [("perfect_window", "zero_ms")],
        "fg": [("perfect_window", "zero_ms")],
    }


def test_team_buff_unknown_mode_fails_loud():
    from gear_optimizer.helpers.song_helpers import team_buff_tiers as tbt

    with pytest.raises(ValueError):
        tbt.build_team_buff_tier_db_batches(
            entries=[{}], calc_song={}, ref_arrays={}, cfg_dict={}, timing_mode="bogus_mode"
        )
    with pytest.raises(ValueError):
        tbt.compute_team_buff_tier_leaderboards(
            entries=[{}], calc_song={}, ref_arrays={}, cfg_dict={}, timing_mode="bogus_mode"
        )


def test_gpu_warmup_songs_do_not_select_a_request_mode():
    from gear_optimizer.solver.taichi_gem.api import ga_operations, skyline_operations

    assert "TimingEnvelopeMode" not in ga_operations._warmup_calc_song()["metadata"]
    assert "TimingEnvelopeMode" not in skyline_operations._warmup_calc_song()["metadata"]
