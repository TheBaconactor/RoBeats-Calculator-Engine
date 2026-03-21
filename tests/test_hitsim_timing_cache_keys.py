from __future__ import annotations

import numpy as np

from gear_optimizer.core.utils import human_hitsim_timing_context, stats_signature
from gear_optimizer.solver.scoring.stats_scoring import _song_cache_key
from gear_optimizer.solver.taichi_gem.api.timeline import _song_timing_cache_key


def _calc_song(*, seed: int, apply_to: str = "ALL", distribution: str = "uniform", great_mode: str = "full") -> dict:
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
            "HumanHitSimSeed": int(seed),
            "HumanHitSimDistribution": str(distribution),
            "HumanHitSimGreatMode": str(great_mode),
        },
        "song_data": {
            "timestamps": timestamps.copy(),
            "fg_timestamps": timestamps.copy(),
        },
    }


def test_human_hitsim_timing_context_is_empty_for_non_all_apply() -> None:
    assert human_hitsim_timing_context(_calc_song(seed=11111, apply_to="FG")) == ("", "", "", 0)


def test_stats_signature_changes_with_hitsim_great_mode() -> None:
    stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Beat": 200,
        "Vibe": 150,
    }

    sig_a = stats_signature(stats, _calc_song(seed=11111, great_mode="full"), "Beat")
    sig_b = stats_signature(stats, _calc_song(seed=11111, great_mode="late"), "Beat")

    assert sig_a != sig_b


def test_song_and_gpu_timeline_cache_keys_change_with_hitsim_great_mode() -> None:
    calc_song_a = _calc_song(seed=11111, great_mode="full")
    calc_song_b = _calc_song(seed=11111, great_mode="late")

    assert _song_cache_key(calc_song_a) != _song_cache_key(calc_song_b)
    assert _song_timing_cache_key(calc_song_a) != _song_timing_cache_key(calc_song_b)
