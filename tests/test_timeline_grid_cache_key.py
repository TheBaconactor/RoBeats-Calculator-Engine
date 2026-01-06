import numpy as np


def test_song_timeline_grid_cache_key_includes_human_hit_sim_seed():
    from gear_optimizer.solver.fever_timeline import SONG_TIMELINE_GRIDS, get_song_timeline_grid

    SONG_TIMELINE_GRIDS.clear()

    ref_arrays = {
        "Fever Time": np.ones(161, dtype=np.float32),
        "Fever Fill Rate": np.ones(161, dtype=np.float32),
    }
    timestamps = np.array([0.0, 0.1, 0.2], dtype=np.float64)

    calc_song1 = {
        "metadata": {
            "Song Name": "CacheKey Song",
            "Last Note Time": 0.2,
            "Long Notes": 0,
            "HumanHitSimSeed": 111,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "late",
        },
        "song_data": {"timestamps": timestamps},
    }

    calc_song2 = {
        "metadata": {
            "Song Name": "CacheKey Song",
            "Last Note Time": 0.2,
            "Long Notes": 0,
            "HumanHitSimSeed": 222,
            "HumanHitSimApplyTo": "ALL",
            "HumanHitSimDistribution": "uniform",
            "HumanHitSimGreatMode": "late",
        },
        "song_data": {"timestamps": timestamps},
    }

    grid1 = get_song_timeline_grid(calc_song1, ref_arrays)
    grid1_again = get_song_timeline_grid(calc_song1, ref_arrays)
    grid2 = get_song_timeline_grid(calc_song2, ref_arrays)

    assert grid1 is grid1_again
    assert grid1 is not grid2
    assert getattr(grid1, "cache_key", None) != getattr(grid2, "cache_key", None)

