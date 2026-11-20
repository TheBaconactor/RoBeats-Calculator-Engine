"""The Base timeline-trace memo is FIFO-bounded, serves repeat keys, and hands out copies.

CPU-only: every scoring/trace dependency is stubbed, so this checks only the memo bookkeeping in
``score_stats_exact_with_timeline_trace`` (the score itself never comes from the memo).
"""

from __future__ import annotations

from types import SimpleNamespace

from gear_optimizer.solver.scoring import exact_rescore
from gear_optimizer.frontier import timeline_cache as timeline_api
from tests.songs_support import make_song


def _install_stubs(monkeypatch) -> list[tuple[int, int, int]]:
    traced: list[tuple[int, int, int]] = []
    frontier_result = SimpleNamespace(cache_key=("unit", "trace-memo"), payload=object())

    monkeypatch.setattr(timeline_api, "build_or_load_timeline_frontier_payload", lambda *_args, **_kwargs: frontier_result)
    monkeypatch.setattr(
        exact_rescore,
        "_best_timeline_score",
        lambda payload, curves, primary, secondary, stats, total_notes: (1_000 + stats["Fever Time"], 0),
    )

    def _trace(*, pool_idx, ft_idx, ff_idx, **_kwargs):
        traced.append((int(ft_idx), int(ff_idx), int(pool_idx)))
        return {
            "frontier_trace": [{"note": int(ft_idx), "ff": int(ff_idx)}],
            "response_surface": [int(ft_idx), int(ff_idx)],
            "raw_fever_fill": 1.0,
        }

    monkeypatch.setattr(exact_rescore, "_timeline_trace_for_payload_surface", _trace)
    return traced


def _score(ft: int, ff: int) -> dict:
    stats = {"Fever Time": ft, "Fever Fill Rate": ff}
    return exact_rescore.score_stats_exact_with_timeline_trace(stats, make_song([0.0, 0.5]), {}, perfect_time=0)


def test_timeline_trace_memo_is_bounded_hits_and_copies(monkeypatch) -> None:
    traced = _install_stubs(monkeypatch)
    monkeypatch.setattr(exact_rescore, "_TIMELINE_TRACE_MEMO", {})
    cap = int(exact_rescore._TIMELINE_TRACE_MEMO_MAX)
    keys = [(ft, ff) for ft in range(161) for ff in range(161)][: cap + cap // 2]

    for ft, ff in keys:
        result = _score(ft, ff)
        assert result["score"] == 1_000 + ft
        assert len(exact_rescore._TIMELINE_TRACE_MEMO) <= cap
    assert len(traced) == len(keys)
    assert len(exact_rescore._TIMELINE_TRACE_MEMO) == cap

    # A key inserted within the last `cap` insertions is still memoized: no new trace.
    recent_ft, recent_ff = keys[-cap]
    first = _score(recent_ft, recent_ff)
    assert len(traced) == len(keys)

    # Hand-outs are copies: mutating one never reaches the memo or later callers.
    first["TimelineFrontier"]["frontier_trace"][0]["note"] = -1
    first["TimelineFrontier"]["response_surface"].append(99)
    again = _score(recent_ft, recent_ff)
    assert len(traced) == len(keys)
    assert again["TimelineFrontier"]["frontier_trace"] == [{"note": recent_ft, "ff": recent_ff}]
    assert again["TimelineFrontier"]["response_surface"] == [recent_ft, recent_ff]

    # The oldest keys were FIFO-evicted and re-trace.
    _score(*keys[0])
    assert len(traced) == len(keys) + 1
    assert len(exact_rescore._TIMELINE_TRACE_MEMO) == cap


def test_base_raw_trace_memo_validates_each_perfect_time_independently(monkeypatch) -> None:
    """Base raw-trace cache avoids re-reconstructing across Perfect Time values without bypassing validation."""
    import numpy as np
    import pytest
    from gear_optimizer.gamedata import stat_curves
    from gear_optimizer.trace import physical_replay, reconstruct
    from gear_optimizer.trace.reconstruct import UnplayableTrace

    monkeypatch.setattr(exact_rescore, "_TIMELINE_TRACE_MEMO", {})
    monkeypatch.setattr(exact_rescore, "_TIMELINE_RAW_TRACE_MEMO", {})
    calls = {"reconstruct": 0, "validate": []}

    def _rec(*_a, **_kw):
        calls["reconstruct"] += 1
        return ({"section": 1, "activation_index": 0},)

    def _val(**kw):
        calls["validate"].append(kw["perfect_time"])
        if kw["perfect_time"] > 0:
            raise UnplayableTrace("base unplayable")

    monkeypatch.setattr(reconstruct, "reconstruct_base_trace", _rec)
    monkeypatch.setattr(physical_replay, "validate_base_physical_replay", _val)
    payload = SimpleNamespace(
        frontier_pool_used=1,
        grid_frontier_body_fever_pool=np.zeros((1, 1), dtype=np.int32),
        grid_frontier_body_normal_pool=np.zeros((1, 1), dtype=np.int32),
        grid_frontier_masks_bits_pool=np.zeros((1, 1, 4), dtype=np.uint32),
    )
    frontier = SimpleNamespace(cache_key=("unit", "raw-split"), payload=payload)
    monkeypatch.setattr(exact_rescore, "_best_timeline_score", lambda *_a, **_kw: (5000, 0))
    song = make_song([0.0, 0.5])
    curves = stat_curves()
    stats = {"Fever Time": 10, "Fever Fill Rate": 10}

    out = exact_rescore.score_stats_exact_with_timeline_trace(stats, song, curves, perfect_time=0, frontier=frontier)
    assert out["score"] == 5000
    with pytest.raises(UnplayableTrace):
        exact_rescore.score_stats_exact_with_timeline_trace(stats, song, curves, perfect_time=120, frontier=frontier)
    assert calls["reconstruct"] == 1
    assert calls["validate"] == [0, 120]
    assert len(exact_rescore._TIMELINE_TRACE_MEMO) == 1
    assert len(exact_rescore._TIMELINE_RAW_TRACE_MEMO) == 1
