"""ZERO_MS_ONLY_TEMP fallback (github issue #125) -- DELETE with the shim.

Pins the temporary behavior that keeps production answering while only ``zero_ms`` exists:
when a calc_song is stamped for the (unbuilt) Perfect-window timing model and no timeline
frontier was prebuilt, ``load_timeline_frontier_payload()`` must NOT raise
``MissingFrontierCacheError`` -- it must fall back to the fixed chart-time (``zero_ms``) payload
and score identically to the independent ``zero_ms`` scorer.

When the real timing model ships and the fallback is removed (see issue #125), delete this file.
"""

from __future__ import annotations

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.scoring.exact_rescore import (
    score_stats_exact_batch,
    score_stats_fixed_timing_exact_batch,
)
from gear_optimizer.solver.timing_envelope import apply_timing_envelope
from gear_optimizer.solver.zero_ms_only_temp import coerce_calc_song_to_zero_ms


def _ref_arrays() -> dict[str, np.ndarray]:
    rows = TOTAL_ROWS + 1
    return {
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 4.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.3, 1.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(0.3, 1.0, rows, dtype=np.float64),
    }


def _calc_song() -> dict:
    timestamps = np.round(np.arange(250, dtype=np.float32) * np.float32(0.1), 3).astype(np.float32)
    return {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {
            "timestamps": timestamps,
            "chart_timestamps": timestamps,
        },
    }


def _stats() -> dict[str, int]:
    return {
        "Perfect Points": 40,
        "Combo Multiplier": 55,
        "Fever Multiplier": 30,
        "Fever Time": 70,
        "Fever Fill Rate": 90,
        "Rush": 20,
        "Flow": 10,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }


def test_coerce_calc_song_to_zero_ms_restamps_without_mutating_source():
    cs = _calc_song()
    apply_timing_envelope(cs, mode="perfect_window")
    assert cs["metadata"]["TimingEnvelopeMode"] == "perfect_window"

    coerced = coerce_calc_song_to_zero_ms(cs)

    assert coerced["metadata"]["TimingEnvelopeMode"] == "zero_ms"
    # Source dict is untouched (shallow copy).
    assert cs["metadata"]["TimingEnvelopeMode"] == "perfect_window"
    # The zero_ms hit timeline IS the chart timeline, so the chart array is shared as-is.
    assert coerced["song_data"]["chart_timestamps"] is cs["song_data"]["chart_timestamps"]


def test_perfect_window_request_falls_back_to_zero_ms_payload_without_prebuilt_frontier(tmp_path, monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import timeline

    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", str(tmp_path))
    timeline.reset_timeline_state()

    # Stamp for the (unbuilt) Perfect-window model; no timeline frontier is prebuilt on this branch.
    cs = _calc_song()
    apply_timing_envelope(cs, mode="perfect_window")
    assert cs["metadata"]["TimingEnvelopeMode"] == "perfect_window"
    ref = _ref_arrays()

    # Pre-fix this raised MissingFrontierCacheError; the temporary fallback must serve zero_ms.
    loaded = timeline.load_timeline_frontier_payload(cs, ref)

    assert loaded.cache_source == "fixed_zero_ms"
    assert loaded.payload.frontier_pool_used > 0
    assert np.all(loaded.payload.grid_frontier_count == 1)
    assert list(tmp_path.glob("*.npz")) == []  # nothing persisted to disk

    stats_rows = [
        _stats(),
        {**_stats(), "Fever Time": 0, "Fever Fill Rate": 0},
        {**_stats(), "Fever Time": TOTAL_ROWS, "Fever Fill Rate": TOTAL_ROWS},
    ]
    # The base score served for the Perfect-window request equals the independent zero_ms scorer.
    cs_zero = _calc_song()
    apply_timing_envelope(cs_zero, mode="zero_ms")
    assert score_stats_exact_batch(stats_rows, cs, ref) == score_stats_fixed_timing_exact_batch(
        stats_rows, cs_zero, ref
    )
