import numpy as np

from gear_optimizer.core.utils import timing_envelope_timing_context
from gear_optimizer.solver.scoring.stats_scoring import _song_cache_key
from gear_optimizer.solver.taichi_gem.api.timeline import _song_timing_cache_key
from gear_optimizer.solver.timing_envelope import apply_timing_envelope


def _calc_song() -> dict:
    timestamps = np.array([0.0, 0.5, 1.0], dtype=np.float64)
    return {
        "metadata": {
            "Song Name": "Timing Envelope Cache Song",
            "Difficulty": "Hard",
            "Primary Color": "Beat",
            "Secondary Color": "Vibe",
            "Last Note Time": float(timestamps[-1]),
            "Long Notes": 0,
        },
        "song_data": {
            "timestamps": timestamps.copy(),
            "chart_timestamps": timestamps.copy(),
            "note_types": np.ones(timestamps.shape[0], dtype=np.int16),
            "lanes": np.arange(timestamps.shape[0], dtype=np.int32),
        },
    }


def test_timing_envelope_context_is_stable_for_identical_chart_inputs() -> None:
    calc_song_a = _calc_song()
    calc_song_b = _calc_song()

    apply_timing_envelope(calc_song_a)
    apply_timing_envelope(calc_song_b)

    assert timing_envelope_timing_context(calc_song_a) == timing_envelope_timing_context(calc_song_b)


def test_stats_and_timeline_cache_keys_are_stable_with_timing_envelope() -> None:
    calc_song_a = _calc_song()
    calc_song_b = _calc_song()
    apply_timing_envelope(calc_song_a)
    apply_timing_envelope(calc_song_b)

    assert _song_cache_key(calc_song_a) == _song_cache_key(calc_song_b)
    assert _song_timing_cache_key(calc_song_a) == _song_timing_cache_key(calc_song_b)


def test_timeline_cache_key_ignores_retired_window_gate_metadata() -> None:
    calc_song_a = _calc_song()
    calc_song_b = _calc_song()
    apply_timing_envelope(calc_song_a)
    apply_timing_envelope(calc_song_b)

    calc_song_a.setdefault("metadata", {})["TimelineAnalysisMaxWindows"] = 0
    calc_song_b.setdefault("metadata", {})["TimelineAnalysisMaxWindows"] = 3

    assert _song_timing_cache_key(calc_song_a) == _song_timing_cache_key(calc_song_b)
