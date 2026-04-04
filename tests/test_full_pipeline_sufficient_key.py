import copy

import numpy as np

from gear_optimizer.core.utils import full_pipeline_signature, stats_signature
from gear_optimizer.solver.hit_simulation import apply_human_hit_sim
from gear_optimizer.solver.scoring.stats_scoring import _song_cache_key, _song_cache_key_for_fg_timeline


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


def test_full_pipeline_signature_includes_hitsim_apply_fg_seed():
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

    cfg_a = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "FG",
            "Seed": "111",
            "Distribution": "uniform",
            "GreatMode": "late",
        }
    }
    cfg_b = {
        "HumanHitSim": {
            "Enabled": "true",
            "ApplyTo": "FG",
            "Seed": "222",
            "Distribution": "uniform",
            "GreatMode": "late",
        }
    }

    assert apply_human_hit_sim(calc_song_a, cfg_dict=cfg_a) is not None
    assert apply_human_hit_sim(calc_song_b, cfg_dict=cfg_b) is not None

    # Baseline song key intentionally ignores ApplyTo=FG seeds (chart-structure driven caches).
    assert _song_cache_key(calc_song_a) == _song_cache_key(calc_song_b)

    # FG timeline caches MUST vary with ApplyTo=FG hit simulation.
    assert _song_cache_key_for_fg_timeline(calc_song_a) != _song_cache_key_for_fg_timeline(calc_song_b)

    # Gem-solver signature ignores ApplyTo=FG hit simulation (base scoring uses chart timestamps).
    assert stats_signature(stats, calc_song_a, selected_color) == stats_signature(stats, calc_song_b, selected_color)

    # Full base+FG sufficient key must include ApplyTo=FG hit simulation settings.
    assert full_pipeline_signature(stats, calc_song_a, selected_color) != full_pipeline_signature(
        stats, calc_song_b, selected_color
    )

