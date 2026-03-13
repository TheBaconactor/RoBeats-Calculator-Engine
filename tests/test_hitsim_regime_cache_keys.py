from __future__ import annotations

import numpy as np

from gear_optimizer.core.utils import human_hitsim_timing_context, stats_signature
from gear_optimizer.solver.scoring.stats_scoring import _song_cache_key
from gear_optimizer.solver.taichi_gem.api.timeline import _song_timing_cache_key


def _calc_song(*, regime_id: str, apply_to: str = "ALL") -> dict:
    timestamps = np.array([0.0, 0.5, 1.0], dtype=np.float64)
    return {
        "metadata": {
            "Song Name": "Hitsim Cache Song",
            "Difficulty": "Hard",
            "Primary Color": "Beat",
            "Secondary Color": "Vibe",
            "Last Note Time": float(timestamps[-1]),
            "Long Notes": 0,
            "HumanHitSimApplied": True,
            "HumanHitSimApplyTo": str(apply_to),
            "HumanHitSimSeed": 11111,
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "full",
            "HumanHitSimRegimeId": str(regime_id),
            "HumanHitSimRegimeFamily": "ftff_boundary_rows",
            "HumanHitSimRegimeScope": "ALL",
        },
        "song_data": {
            "timestamps": timestamps.copy(),
            "fg_timestamps": timestamps.copy(),
        },
    }


def test_human_hitsim_timing_context_is_empty_for_non_all_apply() -> None:
    assert human_hitsim_timing_context(_calc_song(regime_id="exact:a", apply_to="FG")) == ("", "", "", "", "", 0)


def test_stats_signature_changes_with_hitsim_regime_id() -> None:
    stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Beat": 200,
        "Vibe": 150,
    }

    sig_a = stats_signature(stats, _calc_song(regime_id="exact:a"), "Beat")
    sig_b = stats_signature(stats, _calc_song(regime_id="exact:b"), "Beat")

    assert sig_a != sig_b


def test_song_and_gpu_timeline_cache_keys_change_with_hitsim_regime_id() -> None:
    calc_song_a = _calc_song(regime_id="exact:a")
    calc_song_b = _calc_song(regime_id="exact:b")

    assert _song_cache_key(calc_song_a) != _song_cache_key(calc_song_b)
    assert _song_timing_cache_key(calc_song_a) != _song_timing_cache_key(calc_song_b)
