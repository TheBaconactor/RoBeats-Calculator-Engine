"""The Base timeline-trace memo is FIFO-bounded, serves repeat keys, and hands out copies.

CPU-only: every scoring/trace dependency is stubbed, so this checks only the memo bookkeeping in
``score_stats_exact_with_timeline_trace`` (the score itself never comes from the memo).
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from gear_optimizer.solver.scoring import exact_rescore
from gear_optimizer.solver.taichi_gem.api import timeline as timeline_api


def _install_stubs(monkeypatch) -> list[tuple[int, int, int]]:
    traced: list[tuple[int, int, int]] = []
    frontier_result = SimpleNamespace(cache_key=("unit", "trace-memo"), payload=object())

    monkeypatch.setattr(timeline_api, "load_timeline_frontier_payload", lambda *_args, **_kwargs: frontier_result)
    monkeypatch.setattr(exact_rescore, "_frontier_replay_refs", lambda refs: refs)
    monkeypatch.setattr(
        exact_rescore,
        "extract_song_meta",
        lambda _song: SimpleNamespace(primary_color="Rush", secondary_color="Flow"),
    )
    monkeypatch.setattr(
        exact_rescore,
        "_score_stat_inputs",
        lambda stats, *_args: (0, 0, 1.0, 1.0, 1.0, int(stats["FT"]), int(stats["FF"])),
    )
    monkeypatch.setattr(
        exact_rescore,
        "_score_timeline_frontier_payload_vectorized_result",
        lambda **kwargs: (1_000 + int(kwargs["ft_idx"]), 0),
    )

    def _trace(*, pool_idx, ft_idx, ff_idx, **_kwargs):
        traced.append((int(ft_idx), int(ff_idx), int(pool_idx)))
        return {
            "frontier_trace": [{"note": int(ft_idx), "ff": int(ff_idx)}],
            "response_surface": [int(ft_idx), int(ff_idx)],
            "fill_count": 1,
        }

    monkeypatch.setattr(exact_rescore, "_timeline_trace_for_payload_surface", _trace)
    return traced


def _score(ft: int, ff: int) -> dict:
    calc_song = {"metadata": {}, "song_data": {"timestamps": np.asarray([0.0, 0.5], dtype=np.float32)}}
    return exact_rescore.score_stats_exact_with_timeline_trace({"FT": ft, "FF": ff}, calc_song, {})


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
