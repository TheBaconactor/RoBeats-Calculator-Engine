import copy

import numpy as np

from gear_optimizer.core.utils import full_pipeline_signature, stats_signature
from gear_optimizer.solver.scoring.stats_scoring import _song_cache_key, _song_cache_key_for_fg_timeline
from gear_optimizer.solver.timing_envelope import apply_timing_envelope


def _build_calc_song_for_key_tests() -> dict:
    ts = np.array([0.000, 0.050, 0.100, 0.100, 0.120], dtype=np.float64)
    return {
        "metadata": {
            "Song Name": "Sufficient Key Test Song",
            "Difficulty": "Hard",
            "Primary Color": "Beat",
            "Secondary Color": "Vibe",
            "Last Note Time": float(ts[-1]),
            "Long Notes": 0,
        },
        "song_data": {
            "timestamps": ts.copy(),
            "chart_timestamps": ts.copy(),
            "note_types": np.ones(ts.shape[0], dtype=np.int16),
        },
    }


def test_full_pipeline_signature_uses_stable_timing_envelope_context():
    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Beat": 10,
        "Vibe": 20,
    }
    selected_color = "Chill"

    calc_song_a = _build_calc_song_for_key_tests()
    calc_song_b = copy.deepcopy(calc_song_a)

    assert apply_timing_envelope(calc_song_a) is not None
    assert apply_timing_envelope(calc_song_b) is not None

    # Baseline song key is chart-structure driven.
    assert _song_cache_key(calc_song_a) == _song_cache_key(calc_song_b)

    # Deterministic timing-envelope FG streams are stable for identical chart inputs.
    assert _song_cache_key_for_fg_timeline(calc_song_a) == _song_cache_key_for_fg_timeline(calc_song_b)

    # Gem-solver signature uses chart timestamps.
    assert stats_signature(stats, calc_song_a, selected_color) == stats_signature(stats, calc_song_b, selected_color)

    # Full base+FG sufficient key includes the shared timing-envelope context, which is deterministic here.
    assert full_pipeline_signature(stats, calc_song_a, selected_color) == full_pipeline_signature(
        stats, calc_song_b, selected_color
    )
