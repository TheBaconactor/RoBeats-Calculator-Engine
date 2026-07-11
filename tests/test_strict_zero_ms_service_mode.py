"""strict_zero_ms service mode -- the thin gate that makes a deployment serve only zero_ms.

Flag OFF is the default and a pure no-op (every other test runs with it off, unchanged). These pin
the flag-ON coercions (prep sites, request gate, tier re-solve), the startup prebuild skip, and the
stamp-keyed base-score canonicalization -- without touching GPU or building any frontier.

The single monkeypatch point is ``timing_service_mode._ENV``: every helper resolves the flag by
reading that module global at call time, so patching it flips strict mode for every consumer no
matter how it imported the helper.
"""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest

from gear_optimizer.solver import timing_service_mode


@pytest.fixture
def strict_on(monkeypatch):
    monkeypatch.setattr(timing_service_mode, "_ENV", SimpleNamespace(strict_zero_ms=True))


@pytest.fixture
def strict_off(monkeypatch):
    monkeypatch.setattr(timing_service_mode, "_ENV", SimpleNamespace(strict_zero_ms=False))


def test_helpers_off_are_noops(strict_off):
    assert timing_service_mode.strict_zero_ms() is False
    assert timing_service_mode.prepared_timing_mode_override() is None
    assert timing_service_mode.prepared_timing_mode_override("perfect_window") == "perfect_window"
    assert timing_service_mode.enforce_service_timing_mode("perfect_window") == "perfect_window"
    assert timing_service_mode.enforce_service_timing_mode("zero_ms") == "zero_ms"


def test_helpers_on_force_zero_ms(strict_on):
    assert timing_service_mode.strict_zero_ms() is True
    assert timing_service_mode.prepared_timing_mode_override() == "zero_ms"
    assert timing_service_mode.prepared_timing_mode_override("perfect_window") == "zero_ms"
    assert timing_service_mode.enforce_service_timing_mode("perfect_window") == "zero_ms"
    assert timing_service_mode.enforce_service_timing_mode("zero_ms") == "zero_ms"


def test_service_request_gate_coerces_when_strict(strict_on):
    from gear_optimizer import robeatsmeta_service

    assert robeatsmeta_service._normalize_timing_mode("perfect_window") == "zero_ms"
    assert robeatsmeta_service._normalize_timing_mode(None) == "zero_ms"
    assert robeatsmeta_service._normalize_timing_mode("zero_ms") == "zero_ms"
    # Unknown modes still fail loud BEFORE coercion.
    with pytest.raises(robeatsmeta_service.RequestError):
        robeatsmeta_service._normalize_timing_mode("bogus")


def test_service_request_gate_passthrough_when_off(strict_off):
    from gear_optimizer import robeatsmeta_service

    assert robeatsmeta_service._normalize_timing_mode("perfect_window") == "perfect_window"
    assert robeatsmeta_service._normalize_timing_mode("zero_ms") == "zero_ms"


def test_song_preparation_forces_zero_ms_when_strict(strict_on, monkeypatch):
    captured: dict = {}

    def fake_envelope(calc_song, *, mode=None, **_kw):
        captured["mode"] = mode
        return calc_song

    monkeypatch.setattr("gear_optimizer.solver.timing_envelope.apply_timing_envelope", fake_envelope)
    from gear_optimizer.solver import song_preparation

    song_preparation._apply_timing_envelope({"song_data": {}, "metadata": {}})
    assert captured["mode"] == "zero_ms"


def test_song_preparation_defaults_when_off(strict_off, monkeypatch):
    captured: dict = {}

    def fake_envelope(calc_song, *, mode=None, **_kw):
        captured["mode"] = mode
        return calc_song

    monkeypatch.setattr("gear_optimizer.solver.timing_envelope.apply_timing_envelope", fake_envelope)
    from gear_optimizer.solver import song_preparation

    song_preparation._apply_timing_envelope({"song_data": {}, "metadata": {}})
    assert captured["mode"] is None  # main's implicit default (chart metadata -> perfect_window)


def _fake_summary(module):
    return module.TimelineFrontierCachePrebuildSummary()


def test_startup_skips_timeline_prebuild_when_strict(strict_on, monkeypatch):
    from gear_optimizer.solver import cpu_work_manager

    calls = {"timeline": 0, "fg": 0}

    def fake_timeline(**_kw):
        calls["timeline"] += 1
        return _fake_summary(cpu_work_manager)

    def fake_fg(**_kw):
        calls["fg"] += 1
        return _fake_summary(cpu_work_manager)

    monkeypatch.setattr(cpu_work_manager, "run_timeline_frontier_cache_prebuild", fake_timeline)
    monkeypatch.setattr(cpu_work_manager, "run_fg_response_frontier_cache_prebuild", fake_fg)
    cpu_work_manager.run_startup_cpu_work(
        cfg=None, song_queue=["a"], ref_arrays={}, data_root=".", announce_stream=io.StringIO()
    )
    assert calls == {"timeline": 0, "fg": 1}  # timeline (perfect_window) prebuild skipped; FG kept


def test_startup_builds_timeline_prebuild_when_off(strict_off, monkeypatch):
    from gear_optimizer.solver import cpu_work_manager

    calls = {"timeline": 0, "fg": 0}

    def fake_timeline(**_kw):
        calls["timeline"] += 1
        return _fake_summary(cpu_work_manager)

    def fake_fg(**_kw):
        calls["fg"] += 1
        return _fake_summary(cpu_work_manager)

    monkeypatch.setattr(cpu_work_manager, "run_timeline_frontier_cache_prebuild", fake_timeline)
    monkeypatch.setattr(cpu_work_manager, "run_fg_response_frontier_cache_prebuild", fake_fg)
    cpu_work_manager.run_startup_cpu_work(
        cfg=None, song_queue=["a"], ref_arrays={}, data_root=".", announce_stream=io.StringIO()
    )
    assert calls == {"timeline": 1, "fg": 1}  # both prebuilds run, exactly as main today


def test_canonicalize_base_score_zero_ms_uses_fixed_scorer(monkeypatch):
    """The zero_ms base-score branch keys on the calc_song stamp, independent of the deploy flag."""
    from gear_optimizer.helpers.song_helpers import persistence_authority as pa

    monkeypatch.setattr(pa, "score_stats_fixed_timing_exact", lambda stats, cs, ref: 12345)

    def _must_not_run(*_a, **_k):
        raise AssertionError("perfect_window scorer must not run for a zero_ms-stamped calc_song")

    monkeypatch.setattr(pa, "score_stats_exact_with_timeline_trace", _must_not_run)
    out = {"score": 0, "details": {"Stats": {"Beat": 1}, "TimelineFrontier": {"x": 1}}}
    pa._canonicalize_base_score(
        out, calc_song={"metadata": {"TimingEnvelopeMode": "zero_ms"}}, ref_arrays={}
    )
    assert out["score"] == 12345
    assert "TimelineFrontier" not in out["details"]  # zero_ms carries no TimelineFrontier


def test_canonicalize_base_score_perfect_window_unchanged(monkeypatch):
    from gear_optimizer.helpers.song_helpers import persistence_authority as pa

    monkeypatch.setattr(
        pa,
        "score_stats_exact_with_timeline_trace",
        lambda stats, cs, ref: {"score": 999, "TimelineFrontier": {"y": 2}},
    )

    def _must_not_run(*_a, **_k):
        raise AssertionError("fixed scorer must not run for a perfect_window calc_song")

    monkeypatch.setattr(pa, "score_stats_fixed_timing_exact", _must_not_run)
    out = {"score": 0, "details": {"Stats": {"Beat": 1}}}
    pa._canonicalize_base_score(
        out, calc_song={"metadata": {"TimingEnvelopeMode": "perfect_window"}}, ref_arrays={}
    )
    assert out["score"] == 999
    assert out["details"]["TimelineFrontier"] == {"y": 2}
